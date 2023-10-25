from .const import *
from datetime import time, timedelta, datetime
from gc import callbacks
from homeassistant.core import callback
from homeassistant.const import EntityCategory
from homeassistant.components.text import TextEntity, TextMode
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)
from homeassistant.components.number import NumberEntity
from homeassistant.components.number.const import  NumberDeviceClass
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.helpers.service import verify_domain_control
from sonnenbatterie import sonnenbatterie
from sonnenbatterie.timeofuse import timeofuse, timeofuseschedule

TIME_FORMAT="%H:%M:%S"
class SonnenBatteryTOUSchedule(CoordinatorEntity, TextEntity):
    def __init__(self, hass, sonnenbatterie:sonnenbatterie, allSensorsPrefix, model_name, async_add_entities, mainCoordinator):
        self.LOGGER = LOGGER
        self.LOGGER.info("SonnenBatteryTOUSchedule init with prefix "+allSensorsPrefix)
        self._unique_id= "{}{}".format(allSensorsPrefix,"tou_schedule")
        self.entity_id = self._unique_id
        self.LOGGER.info("SonnenBatteryTOUSchedule id is "+self._unique_id)
        self._name = "Time Of Use schedule"
        self._attr_mode = TextMode.TEXT
        self._attr_native_value = "Not yet retrieved"
        self.sonnenbatterie = sonnenbatterie
        self.hass = hass
        self.mainCoordinator = mainCoordinator
        self.model_name = model_name
        self._attr_icon = "mdi:clock"
        self._coordinator = DataUpdateCoordinator(hass, LOGGER, name="Sonnen battery special sensors time of use", update_interval=timedelta(seconds=DEFAULT_UPDATE_FREQUENCY_TOU_SCHEDULE), update_method=self.async_handle_coordinator_update)
        super().__init__(self._coordinator)
        async_add_entities([self])
        # register the services
        if not hass.services.has_service(DOMAIN, SERVICE_SET_TOU_SCHEDULE) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_TOU_SCHEDULE, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_tou_schedule),
                # we try and have voluptuous make the more lower case before checking it's in the list
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_TOU_START): vol.All(
                            vol.Coerce(str), vol.Datetime(TIME_FORMAT)),
                        vol.Required(SERVICE_ATTR_TOU_END): vol.All(
                            vol.Coerce(str), vol.Datetime(TIME_FORMAT)),
                        vol.Required(SERVICE_ATTR_TOU_MAX_POWER_IN_KW): vol.All(
                            vol.Coerce(int), vol.Range(min=TOU_SCHEDULE_MIN_INCOMMING_POWER_IN_KW, max=TOU_SCHEDULE_MAX_INCOMMING_POWER_IN_KW)
                            ),
                    }
                ),
            ) 
        self.LOGGER.info("SonnenBatteryTOUSchedule added service "+SERVICE_SET_TOU_SCHEDULE)
        if not hass.services.has_service(DOMAIN, SERVICE_GET_TOU_UPDATE_FREQUENCY) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_GET_TOU_UPDATE_FREQUENCY, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_tou_update_frequency),
                # we try and have voluptuous make the more lower case before checking it's in the list
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_GET_TOU_UPDATE_FREQUENCY): vol.All(
                            vol.Coerce(int), vol.Range(min=10, max=300),
                        )
                    }
                ),
            ) 
        self.LOGGER.info("SonnenBatteryOperatingMode setup service "+SERVICE_GET_TOU_UPDATE_FREQUENCY)



        self.LOGGER.info("SonnenBatteryTOUSchedule initialised")
       
    def setUpdateInternal(self, updateIntervalInSeconds:int) :
        self._coordinator.update_interval = timedelta(seconds=updateIntervalInSeconds)        
        self.LOGGER.warn("SonnenBatteryTOUSchedule setUpdateInternal setting frequency "+(str(updateIntervalInSeconds)))


    async def sonnenbatterie_set_tou_update_frequency(self, call):
        self.LOGGER.debug("SonnenBatteryTOUSchedule sonnenbatterie_set_tou_update_frequency  starting")
        newFrequency = int(call.data[SERVICE_ATTR_GET_TOU_UPDATE_FREQUENCY])
        await self.hass.async_add_executor_job(self.setUpdateInternal, newFrequency) 

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self.mainCoordinator.initialDeviceInfo
    
    def set_tou_schedule(self, touStart:time, touEnd:time, touMaxPowerInKw:int):
        self.LOGGER.info("SonnenBatteryTOUSchedule set_tou_schedule start time is "+time.strftime(touStart, TIME_FORMAT)+" end time is "+time.strftime(touEnd, TIME_FORMAT)+", max powerr in kw is "+str(touMaxPowerInKw))
        touMaxPower = touMaxPowerInKw * 1000
        touschedule =  timeofuseschedule()
        touschedule.add_entry(timeofuse(touStart, touEnd, touMaxPower))
        touString = touschedule.get_as_string()
        self.LOGGER.debug("SonnenBatteryTOUSchedule set_tou_schedule setting schedule to "+touString)
        self.sonnenbatterie.set_time_of_use_schedule_from_json_objects(touschedule.get_as_tou_schedule())
        self.update_state()


    async def sonnenbatterie_set_tou_schedule(self, call):
        self.LOGGER.debug("SonnenBatteryTOUSchedule sonnenbatterie_set_tou_schedule starting")
        touStartStr = call.data[SERVICE_ATTR_TOU_START]
        touEndStr = call.data[SERVICE_ATTR_TOU_END]
        touMaxPowerInKw = call.data[SERVICE_ATTR_TOU_MAX_POWER_IN_KW]
        self.LOGGER.info("SonnenBatteryTOUSchedule sonnenbatterie_set_tou_schedule start time is "+touStartStr+" end time is "+touEndStr+", max powerr in kw is "+str(touMaxPowerInKw))
        touStart = datetime.strptime(touStartStr, TIME_FORMAT).time()
        touEnd = datetime.strptime(touEndStr, TIME_FORMAT).time()
        await self.hass.async_add_executor_job(self.set_tou_schedule, touStart, touEnd, touMaxPowerInKw)

    @callback
    async def async_handle_coordinator_update(self) -> None:
        await self.hass.async_add_executor_job(self.update_state)

    def update_state(self):
        try:
            self.LOGGER.debug("SonnenBatteryTOUSchedule update state")
            schedule = self.sonnenbatterie.get_time_of_use_schedule_as_schedule()
            self.LOGGER.warn("SonnenBatteryTOUSchedule update state schedule is "+schedule.get_as_string())
            # this will return an array, for now we're assuming the following
            # if there are no entries then there is no TOU schedule
            # if there is one entry then the tou start and end come from that, the max power comes from the first
            # if there are two or more entries then the tou start comes form the first and the end from the last, the max power comes from the first
            # (this assumes that the entries are time sorted, which the underlying driver shoudl handle for us)
            if (schedule.entry_count() == 0) :
                # nothing, return
                start="00:00"
                end = "00:00"
                maxpower = 0
                return 
            elif (schedule.entry_count() == 1) :
                entryfirst = schedule.get_tou_entry(0)
                start = entryfirst.get_start_time_as_string()
                end = entryfirst.get_stop_time_as_string()
                maxpower = entryfirst.get_max_power()
            else :
                entryfirst = schedule.get_tou_entry(0)
                entrylast = schedule.get_tou_entry(schedule.entry_count()-1)
                start = entrylast.get_start_time_as_string()
                end = entryfirst.get_stop_time_as_string()
                maxpower = entryfirst.get_max_power()
            tou_schedule="Start "+start+", end "+end+", max power "+str(maxpower)
            self._attr_native_value=tou_schedule
            self.schedule_update_ha_state()
        except Exception as e:
            self.LOGGER.warn("SonnenBatteryTOUSchedule Unable to get sonnenbatterytouschedule, type "+str(type(e))+", details "+str(e))

    @property
    def name(self):
        return self._name
    
    @property
    def unique_id(self) -> str:
        return self._unique_id
        
    @property
    def should_poll(self):
        return False

    @property
    def entity_category(self):
        return EntityCategory.CONFIG
    
    @property
    def native_unit_of_measurement(self) -> str:
        return None