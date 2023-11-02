import threading
import asyncio
from .const import *
from .setting_manager import SonnenSettingsManager
from .sonnen_flow_rates import SONNEN_BATTERY_TO_MAX_CHARGE, SONNEN_BATTERY_TO_MAX_DISCHARGE, SONNEN_MODEL_UNKNOWN_NAME_MAX_CHARGE, SONNEN_MODEL_UNKNOWN_NAME_MAX_DISCHARGE
from datetime import time, timedelta
from gc import callbacks
from sonnenbatterie import sonnenbatterie
from .sonnen_operating_modes_map import SONNEN_BATTERY_TO_OPERATING_MODES, SONNEN_BATTERY_ALL_OPERATING_MODES, SONNEN_BATTERY_NAMES_MAPPINGS,SONNEN_MODE_NICKNAME_TO_MODE_NAME_DEFAULT 
from homeassistant.core import callback
from homeassistant.const import EntityCategory
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.text import TextEntity, TextMode
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)

from homeassistant.helpers.service import verify_domain_control
class SonnenBatteryOperatingMode(CoordinatorEntity, SelectEntity, TextEntity):
    def __init__(self, hass, sonnenbatterie:sonnenbatterie,  allSensorsPrefix:str, model_name:str,  async_add_entities, mainCoordinator, settingManager:SonnenSettingsManager):
        self.LOGGER = LOGGER
        self.LOGGER.info("SonnenBatteryOperatingMode init with prefix "+allSensorsPrefix)
        self._unique_id= "{}{}".format(allSensorsPrefix,"operating_mode")
        self.entity_id=self._unique_id
        self.LOGGER.warn("SonnenBatteryOperatingMode id is "+self._unique_id+" model_name is "+model_name)
        self._attr_has_entity_name = True
        self._name = "Operating mode"
        self._attr_mode = TextMode.TEXT
        self._attr_entity_config = EntityCategory.CONFIG
        self._enabled_by_default = True
        self._current_option = "None"
        self.sonnenbatterie = sonnenbatterie
        self.hass = hass
        self.mainCoordinator = mainCoordinator
        self._device_info = self.mainCoordinator.initialDeviceInfo
        self.model_name = model_name
        self._options = SONNEN_BATTERY_TO_OPERATING_MODES.get(self.mainCoordinator.model_name, SONNEN_BATTERY_ALL_OPERATING_MODES) 
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:auto-mode"
        self._settingManager = settingManager
        self._coordinator = DataUpdateCoordinator(hass, LOGGER, name="Sonnen battery special sensors operating mode", update_interval=timedelta(seconds=DEFAULT_UPDATE_FREQUENCY_OPERATING_MODE), update_method=self.async_handle_coordinator_update)
        tempNamesMappings = SONNEN_BATTERY_NAMES_MAPPINGS.get(self.mainCoordinator.model_name, SONNEN_MODE_NICKNAME_TO_MODE_NAME_DEFAULT)
        self.max_charge_rate = SONNEN_BATTERY_TO_MAX_CHARGE.get(self.mainCoordinator.model_name, SONNEN_MODEL_UNKNOWN_NAME_MAX_CHARGE)
        self.max_discharge_rate = SONNEN_BATTERY_TO_MAX_DISCHARGE.get(self.mainCoordinator.model_name, SONNEN_MODEL_UNKNOWN_NAME_MAX_DISCHARGE)
        # now map the temp names to lower case keys
        self.modeNicknamesToModeName = {k.lower():v for k,v in tempNamesMappings.items()}
        self.LOGGER.info("SonnenBatteryOperatingMode node nicknames to modes for model_name "+model_name+" is "+str(self.modeNicknamesToModeName))
        super().__init__(self._coordinator)
        async_add_entities([self])
        # register the services
        if not hass.services.has_service(DOMAIN, SERVICE_SET_OPERATING_MODE) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_OPERATING_MODE, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_operating_mode_by_nickname_async),
                # we try and have voluptuous make the more lower case before checking it's in the list
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_OPERATING_MODE_MODE): vol.All(
                            vol.Coerce(str), vol.util.Lower, vol.In(self.modeNicknamesToModeName),
                        )
                    }
                ),
            ) 
        self.LOGGER.debug("SonnenBatteryOperatingMode setup service "+SERVICE_SET_OPERATING_MODE)

        # not really sure where this one should fit, there is no directly associated entity so for now let's put it
        # here as it's relevant for manual operation mode which is set here.
        if not hass.services.has_service(DOMAIN, SERVICE_SET_FLOW_RATE) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_FLOW_RATE, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_flow_rate),
                # we try and have voluptuous make the more lower case before checking it's in the list
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_FLOW_RATE): vol.All(
                          vol.Coerce(int), vol.Range(min=self.max_charge_rate, max=self.max_discharge_rate)
                        )
                    }
                ),
            ) 
        self.LOGGER.debug("SonnenBatteryOperatingMode setup service "+SERVICE_SET_FLOW_RATE) 

        if not hass.services.has_service(DOMAIN, SERVICE_GET_OPERATING_MODE_UPDATE_FREQUENCY) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_GET_OPERATING_MODE_UPDATE_FREQUENCY, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_operating_mode_update_frequency),
                # we try and have voluptuous make the more lower case before checking it's in the list
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_GET_OPERATING_MODE_UPDATE_FREQUENCY): vol.All(
                            vol.Coerce(int), vol.Range(min=10, max=300),
                        )
                    }
                ),
            ) 
        self.LOGGER.debug("SonnenBatteryOperatingMode setup service "+SERVICE_GET_OPERATING_MODE_UPDATE_FREQUENCY)
        self.LOGGER.info("SonnenBatteryOperatingMode initialised, doing initial update")
        self.update_state()
        self.LOGGER.info("SonnenBatteryOperatingMode initialised, completed initial update")


   
    def setUpdateInternal(self, updateIntervalInSeconds:int) :
        self._coordinator.update_interval = timedelta(seconds=updateIntervalInSeconds)
        self.LOGGER.info("SonnenBatteryOperatingMode setUpdateInternal setting frequency "+(str(updateIntervalInSeconds)))

    async def sonnenbatterie_set_operating_mode_update_frequency(self, call):
        self.LOGGER.debug("SonnenBatteryOperatingMode sonnenbatterie_set_operating_mode_update_frequency  starting")
        newFrequency = int(call.data[SERVICE_ATTR_GET_OPERATING_MODE_UPDATE_FREQUENCY])
        await self.hass.async_add_executor_job(self.setUpdateInternal, newFrequency)
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device_info
    
    @callback
    async def async_handle_coordinator_update(self) -> None:
        self.LOGGER.debug("SonnenBatteryOperatingMode async_handle_coordinator_update called")
        await self.hass.async_add_executor_job(self.update_state)

    def update_state(self):
        """Handle updated data from the coordinator."""
        self.LOGGER.debug("SonnenBatteryOperatingMode update state starting")
        try:
            current_mode = self.sonnenbatterie.get_operating_mode_name() 
            self._current_option = f"{current_mode}"
            self.LOGGER.debug("SonnenBatteryOperatingMode update state retrieved "+self._current_option)  
            self.async_write_ha_state() 
            self.LOGGER.debug("SonnenBatteryOperatingMode update state triggered HA update")
        except Exception as e:
            LOGGER.warn("SonnenBatteryOperatingMode Unable to get operating mode, type "+str(type(e))+", details "+str(e))   

    def set_operating_mode_by_nickname_sync(self, modeNickname):
        mode = self.modeNicknamesToModeName.get(modeNickname)
        self.LOGGER.info("SonnenBatteryOperatingMode setting mode with nickname "+modeNickname+" which has mapped to mode "+mode)
        self.set_operating_mode_sync(mode)

    def set_operating_mode_sync(self, mode):
        self.LOGGER.info("SonnenBatteryOperatingMode setting to mode "+mode)
        try:
            self.sonnenbatterie.set_operating_mode_by_name(mode)
        except Exception as e:
            self.LOGGER.warn("SonnenBatteryOperatingMode Unable to set operating mode "+mode+", type "+str(type(e))+", details "+str(e))     
        # we may have changed it, update the state
        self.update_state()
        #self.schedule_update_ha_state()

    async def sonnenbatterie_set_operating_mode_by_nickname_async(self, call):
        self.LOGGER.debug("SonnenBatteryOperatingMode sonnenbatterie_set_operating_mode set operating mode starting")
        modeNickname = str(call.data[SERVICE_ATTR_OPERATING_MODE_MODE]).lower()
        self.LOGGER.info("SonnenBatteryOperatingMode sonnenbatterie_set_operating_mode set operating mode setting nickname "+modeNickname)
        mode = self.modeNicknamesToModeName.get(modeNickname)
        self.LOGGER.info("SonnenBatteryOperatingMode setting mode with nickname "+modeNickname+" which has mapped to mode "+mode)
        setLambda = lambda: self.sonnenbatterie.set_operating_mode_by_name(mode)
        checkLambda = lambda: self.sonnenbatterie.get_operating_mode_name() 
        postLambda= lambda: self.update_state()
        await self._settingManager.setDesiredSetting(settingName=SETTING_MANAGER_OPERATING_MODE_NAME, targetValue=mode, settingTargetLambda=setLambda, checkTargetLambda=checkLambda, postSetLambda=postLambda, retryInterval=10, retryCount=5)
        self.LOGGER.info("SonnenBatteryOperatingMode scheduled setting to mode "+mode) 

    def set_flow_rate(self, flowRate):
        # a negative flow rate means charging, and so has to be converted to a postive value before being handed to the charge call
        # a positinve number means discharging and can be used directly
        self.LOGGER.debug("SonnenBatteryOperatingMode set_flow_rate set flow rate to "+str(flowRate))
        try:
            if flowRate < 0 :
                self.LOGGER.info("SonnenBatteryOperatingMode set_flow_rate set charge rate to "+str(flowRate *-1))
                self.sonnenbatterie.set_charge(flowRate * -1)
            else:
                self.LOGGER.info("SonnenBatteryOperatingMode set_flow_rate set discharge rate to "+str(flowRate))
                self.sonnenbatterie.set_discharge(flowRate)
        except Exception as e:
            self.LOGGER.warn("SonnenBatteryOperatingMode Unable to set flow rate "+str(type(e))+", details "+str(e))     
        # as there is no directly connected entity here no need to update

    async def sonnenbatterie_set_flow_rate(self, call):
        # the vol stuff shoudl prevent this being out of bounds
        self.LOGGER.debug("SonnenBatteryOperatingMode sonnenbatterie_set_flow_rate set flow rate starting")
        flowRate = int(call.data[SERVICE_ATTR_FLOW_RATE])
        self.LOGGER.debug("SonnenBatteryOperatingMode sonnenbatterie_set_flow_rate set flow rate to "+str(flowRate))
        await self.hass.async_add_executor_job(self.set_flow_rate, flowRate)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.mainCoordinator.serial)}
        }
    
    @property
    def name(self):
        return self._name
    
    @property
    def unique_id(self) -> str:
        return self._unique_id
    
    @property
    def current_option(self) -> str:
        return self._current_option
    
    @property
    def options(self) -> list:
        return self._options
    
    @property
    def native_value(self) -> str:
        return self.current_option
    
    @property
    def should_poll(self):
        return False

    @property
    def entity_category(self):
        return EntityCategory.CONFIG
    
    @property
    def native_unit_of_measurement(self) -> str:
        return None
    
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        modeNickname = option.lower()
        self.LOGGER.info("SonnenBatteryOperatingMode async_select_option mode changing to "+modeNickname)
        await self.hass.async_add_executor_job(self.set_operating_mode_by_nickname_sync. modeNickname)

    


