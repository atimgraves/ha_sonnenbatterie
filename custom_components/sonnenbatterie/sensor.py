import requests
import traceback
from datetime import datetime
import sys
# pylint: disable=unused-wildcard-import
from .const import *
from .mappings import SBmap
from .sonnen_batterie_sensor import SonnenBatterieSensor
from .sonnen_special_entities import SonnenSpecialEntities

# pylint: enable=unused-wildcard-import
import threading
import time
from homeassistant.helpers import config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.reload import async_setup_reload_service
#from homeassistant.helpers.device_registry import DeviceInfo ##this seems to be the way in some of the next updates...?
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass
)

# pylint: disable=no-name-in-module
from sonnenbatterie import sonnenbatterie
# pylint: enable=no-name-in-module

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_IP_ADDRESS,
    EVENT_HOMEASSISTANT_STOP,
    CONF_SCAN_INTERVAL,
)


_LOGGER = logging.getLogger(__name__)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    ## we dont have anything special going on.. unload should just work, right?
    ##bridge = hass.data[DOMAIN].pop(entry.data['host'])

    return 

async def async_setup_entry(hass, config_entry,async_add_entities):
    """Set up the sensor platform."""
    LOGGER.info('SETUP_ENTRY')
    #await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    username = config_entry.data.get(CONF_USERNAME)
    password = config_entry.data.get(CONF_PASSWORD)
    ipaddress = config_entry.data.get(CONF_IP_ADDRESS)
    updateIntervalSeconds = config_entry.options.get(CONF_SCAN_INTERVAL)
    debug_mode = config_entry.options.get(ATTR_SONNEN_DEBUG)

    def _internal_setup(_username, _password, _ipaddress):
        return sonnenbatterie(_username, _password, _ipaddress)

    sonnenInst = await hass.async_add_executor_job(_internal_setup, username, password, ipaddress)
    updateIntervalSeconds = updateIntervalSeconds or 1
    LOGGER.info("{0} - UPDATEINTERVAL: {1}".format(DOMAIN, updateIntervalSeconds))

    """ The Coordinator is called from HA for updates from API """
    coordinator = SonnenBatterieCoordinator(hass, sonnenInst, async_add_entities, updateIntervalSeconds, debug_mode,config_entry.entry_id)

    await coordinator.async_config_entry_first_refresh()

    LOGGER.info("Preparing special entities")
    sonnenspecialentities = SonnenSpecialEntities(hass, sonnenInst, async_add_entities, coordinator)
    await sonnenspecialentities.start() 
    LOGGER.info("Prepared special entities")    
    LOGGER.info('Init done')
    return True

def generateDeviceInfo(configentry_id,systemdata):

    model="unknown"
    serial="unknown"
    version="unknown"
    
    if "ERP_ArticleName" in systemdata:
        model=systemdata["ERP_ArticleName"]
    if "DE_Ticket_Number" in systemdata:
        serial=systemdata["DE_Ticket_Number"]
    if "software_version" in systemdata:
        version=systemdata["software_version"]


    devicename=devicename="{}_{}".format(DOMAIN, serial)

    return DeviceInfo(
                identifiers={(DOMAIN, configentry_id)},
                manufacturer="Sonnen",
                model=model,
                name=devicename,
                sw_version=version,
                #identifiers={
                #    # Serial numbers are unique identifiers within a specific domain
                #    (DOMAIN, self._devicename)
                #},
                #name=self.name,
                #manufacturer=self.light.manufacturername,
                #model=self.light.productname,
                #sw_version=self.light.swversion,
                #via_device=(hue.DOMAIN, self.api.bridgeid),
            )



class SonnenBatterieCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, sbInst, async_add_entities, updateIntervalSeconds, debug_mode,device_id):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="SonnenBatterieCoordinator",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=updateIntervalSeconds),
        )
        self.sensor=None
        self.hass = hass
        self.latestData = {}
        self.disabledSensors = []
        self.device_id=device_id;

        self.stopped = False
        
        #self.sensor = sensor
        self.sbInst: sonnenbatterie = sbInst
        self.meterSensors = {}
        self.updateIntervalSeconds = updateIntervalSeconds
        self.async_add_entities = async_add_entities
        self.debug = debug_mode
        self.fullLogsAlreadySent = False

        # fixed value, percentage of total installed power reserved for
        # internal battery system purposes
        self.reservedFactor = 7.0

        # placeholders, will be filled later
        self.serial = ""
        self.model_name = ""
        self.allSensorsPrefix = ""
        self.deviceName="to be set"
        self.initialDeviceInfo = None
        
    async def updateData(self) -> bool:
        try:        ##ignore errors here, may be transient
            self.latestData["battery"]        = await self.hass.async_add_executor_job(self.sbInst.get_battery);
            self.latestData["battery_system"] = await self.hass.async_add_executor_job(self.sbInst.get_batterysystem);
            self.latestData["inverter"]       = await self.hass.async_add_executor_job(self.sbInst.get_inverter);
            self.latestData["powermeter"]     = await self.hass.async_add_executor_job(self.sbInst.get_powermeter);
            self.latestData["status"]         = await self.hass.async_add_executor_job(self.sbInst.get_status);
            self.latestData["systemdata"]     = await self.hass.async_add_executor_job(self.sbInst.get_systemdata);
            # report if we suceeded or not, the calling cose can then decide how to progress
            resp =  True 
        except requests.exceptions.Timeout as te:
            LOGGER.warn("Timeout getting data "+str(type(te))+", details "+str(te))    
            resp =  False
        except requests.exceptions.ConnectionError as ce:
            LOGGER.warn("Connection error getting data "+str(type(ce))+", details "+str(ce))    
            resp =  False
        except:
            e = traceback.format_exc()
            LOGGER.error(e)
            resp =  False
        if self.debug:
            self.SendAllDataToLog();
        return resp

       

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        await self.updateData()
        self.parse()
        
        #Create/Update the Main Sensor, named after the battery serial
        systemdata = self.latestData["systemdata"]
        deviceinfo=generateDeviceInfo(self.device_id,systemdata)

        # save it away for later use by spoecial entities
        self.initialDeviceInfo = deviceinfo
            
        serial = systemdata["DE_Ticket_Number"]
        if self.sensor is None:
            self.sensor =  SonnenBatterieSensor(id="sensor.{0}_{1}".format(DOMAIN, serial),deviceinfo=deviceinfo,coordinator=self,name=serial)
            self.async_add_entities([self.sensor])


        statedisplay = "standby"
        if self.latestData["status"]["BatteryCharging"]:
            statedisplay = "charging"
        elif self.latestData["status"]["BatteryDischarging"]:
            statedisplay = "discharging"

        # let's do this just once
        if self.model_name == "":
            if "ERP_ArticleName" in self.latestData["systemdata"]:
                self.model_name = self.latestData["systemdata"]["ERP_ArticleName"]
            else:
                self.model_name = "UNKNOWN"
        if self.serial == "":
            if "DE_Ticket_Number" in self.latestData["systemdata"]:
                self.serial = self.latestData["systemdata"]["DE_Ticket_Number"]
            else:
                self.serial = "UNKNOWN"
            self.allSensorsPrefix = "sensor.{}_{}_".format(DOMAIN, self.serial)
            self.deviceName = "{}_{}".format(DOMAIN, self.serial)

        self.sensor.set_state(statedisplay)
        self.sensor.set_attributes(self.latestData["systemdata"])
        #finish Update/Create Main Sensor

        #update all other entities/sensors
        self.AddOrUpdateEntities()
        

    def parse(self):
        meters = self.latestData["powermeter"]
        battery_system = self.latestData["battery_system"]

        attr = {}
        for meter in meters:
            prefix = "{0}_{1}_{2}-".format(meter['direction'],meter['deviceid'],meter['channel'])
            for name in meter:
                parmName = prefix+name
                attr[parmName] = meter[name]

        bat_sys_dict = flattenObj("battery_system","-",battery_system)
        attr.update(bat_sys_dict)

    def walkEntities(self, entities, parents=[], key=""):
        if "sensor" in entities:
            # only check if we haven't already disabled the sensor
            if entities["sensor"] not in self.disabledSensors:
                # check whether key exists
                lookup = self.latestData
                for section in parents:
                    if section in lookup:
                        # move down to next section
                        lookup = lookup[section]
                    else:
                        #section not found, disable sensor
                        self.disabledSensors.append(entities["sensor"])
                        LOGGER.warning("'{}' not in {} -> disabled".format(entities["sensor"], "/".join(parents) ))
                        return

                # when we get here 'lookup' already is the value we're looking for
                # first, calculate the actual value
                if "convert" in entities:
                    try:
                        real_val = entities["convert"](lookup)
                    except:
                        LOGGER.critical("Wrong conversion info for '{}' in {} -> sending raw value".format(key, "/".join(parents)))
                        real_val = lookup
                else:
                    real_val = lookup

                self._AddOrUpdateEntity(
                    "{}{}".format(self.allSensorsPrefix, entities["sensor"]),
                    entities["friendly_name"],
                    real_val,
                    entities["unit"],
                    entities["class"]
                )

                # add alias names if needed
                if "aka" in entities:
                    for altname in entities["aka"]:
                        self._AddOrUpdateEntity(
                            "{}{}".format(self.allSensorsPrefix, altname),
                            "{} (alias)".format(entities["friendly_name"]),
                            real_val,
                            entities["unit"],
                            entities["class"]
                        )

                # do we need to add in/out values?
                if "inout" in entities:
                    val_in = abs(real_val) if real_val < 0 else 0
                    val_out = real_val if real_val > 0 else 0
                    sensor_base = entities["sensor"][:entities["sensor"].rfind("_")+1]
                    self._AddOrUpdateEntity(
                        "{}{}input".format(self.allSensorsPrefix, sensor_base),
                        "{} (in)".format(entities["friendly_name"]),
                        val_in,
                        entities["unit"],
                        entities["class"]
                    )
                    self._AddOrUpdateEntity(
                        "{}{}output".format(self.allSensorsPrefix, sensor_base),
                        "{} (out)".format(entities["friendly_name"]),
                        val_out,
                        entities["unit"],
                        entities["class"]
                    )

        else:
            # recursively check deeper down
            for elem in entities:
                LOGGER.info("Descending into '{}'".format(elem))
                # push current path to "stack"
                parents.append(elem)
                self.walkEntities(entities[elem], parents, elem)
                # pop path from stack to prevent ever growing path array
                parents.remove(elem)

    def _AddOrUpdateEntity(self,id,friendlyname,value,unit,device_class):
        if id in self.meterSensors:
            sensor = self.meterSensors[id]
            sensor.set_state(value)
        else:
            deviceinfo=generateDeviceInfo(self.device_id,self.latestData["systemdata"] )

            
            sensor = SonnenBatterieSensor(id=id,deviceinfo=deviceinfo,coordinator=self,name=friendlyname)
            sensor.set_attributes(
                {
                    "unit_of_measurement": unit,
                    "device_class":        device_class,
                    "friendly_name":       friendlyname,
                    "state_class":         "measurement"
                }
            )
            self.async_add_entities([sensor])
            self.meterSensors[id] = sensor

    def AddOrUpdateEntities(self):
        """ (almost) all sensors in one go """
        self.walkEntities(SBmap)

        """ some manually calculated values """
        val_module_capacity      = int(self.latestData['battery_system']['battery_system']['system']['storage_capacity_per_module'])
        val_modulecount          = int(self.latestData['battery_system']['modules'])
        total_installed_capacity = int(val_modulecount * val_module_capacity)

        """" Battery Real Capacity Calc """
        sensorname   = "{}{}".format(self.allSensorsPrefix, "state_total_capacity_real")
        unitname     = "Wh"
        friendlyname = "Total Capacity Real"
        self._AddOrUpdateEntity(sensorname, friendlyname, total_installed_capacity, unitname, SensorDeviceClass.ENERGY)

        calc_reservedcapacity = int(total_installed_capacity * (self.reservedFactor / 100.0))
        sensorname   = "{}{}".format(self.allSensorsPrefix, "state_total_capacity_usable")
        unitname     = "Wh"
        friendlyname = "Total Capacity Usable"
        self._AddOrUpdateEntity(sensorname, friendlyname, total_installed_capacity - calc_reservedcapacity, unitname, SensorDeviceClass.ENERGY)

        calc_remainingcapacity = int(total_installed_capacity * self.latestData["status"]["RSOC"]) / 100.0
        sensorname   = "{}{}".format(self.allSensorsPrefix, "state_remaining_capacity_real")
        unitname     = "Wh"
        friendlyname = "Remaining Capacity Real"
        self._AddOrUpdateEntity(sensorname, friendlyname, calc_remainingcapacity, unitname, SensorDeviceClass.ENERGY)

        calc_remainingcapacity_usable = int(max(0, calc_remainingcapacity - calc_reservedcapacity))
        sensorname   = "{}{}".format(self.allSensorsPrefix, "state_remaining_capacity_usable")
        unitname     = "Wh"
        friendlyname = "Remaining Capacity Usable"
        self._AddOrUpdateEntity(sensorname, friendlyname, calc_remainingcapacity_usable, unitname, SensorDeviceClass.ENERGY)

        """powermeter values"""
        for meter in self.latestData["powermeter"]:
            sensornamePrefix = "{}meter_{}_{}_{}".format(self.allSensorsPrefix, meter['direction'], meter['deviceid'], meter['channel'])
            sensornamePrefix = sensornamePrefix.lower()
            generateSensorsFor = {
                "a_l1",
                "a_l2",
                "a_l3",
                "v_l1_l2",
                "v_l1_n",
                "v_l2_l3",
                "v_l2_n",
                "v_l3_l1",
                "v_l3_n",
                "w_l1",
                "w_l2",
                "w_l3",
                "w_total",
            }

            for sensormeter in generateSensorsFor:
                sensorname = "{}_{}".format(sensornamePrefix, sensormeter)
                val = round(meter[sensormeter],2)
                unitname = (sensormeter[0]+"").upper()
                device_class = SensorDeviceClass.POWER
                if unitname == "V":
                    device_class = SensorDeviceClass.VOLTAGE
                elif unitname == "A":
                    device_class=SensorDeviceClass.CURRENT
                friendlyname = "{0} {1}".format(meter['direction'], sensormeter)
                self._AddOrUpdateEntity(
                    sensorname,
                    friendlyname,
                    val,
                    unitname,
                    device_class
                )

    def SendAllDataToLog(self):
        """
            Since we're in "debug" mode, send all data to the log so we dont' have to search for the
            variable we're looking for if it's not where we expect it to be
        """
        if not self.fullLogsAlreadySent:
            LOGGER.warning("Powermeter data:")
            LOGGER.warning(self.latestData["powermeter"])
            LOGGER.warning("Battery system data:")
            LOGGER.warning(self.latestData["battery_system"])
            LOGGER.warning("Inverter:")
            LOGGER.warning(self.latestData["inverter"])
            LOGGER.warning("System data:")
            LOGGER.warning(self.latestData["systemdata"])
            LOGGER.warning("Status:")
            LOGGER.warning(self.latestData["status"])
            LOGGER.warning("Battery:")
            LOGGER.warning(self.latestData["battery"])
            self.fullLogsAlreadySent = True



