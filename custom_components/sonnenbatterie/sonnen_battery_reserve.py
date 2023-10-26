import threading
import asyncio
from .const import *
from datetime import time, timedelta
from gc import callbacks
from sonnenbatterie import sonnenbatterie
from homeassistant.core import callback
from homeassistant.const import EntityCategory
from homeassistant.components.number import NumberEntity, NumberMode, NumberDeviceClass
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.service import verify_domain_control

class SonnenBatteryReserve(CoordinatorEntity, NumberEntity):
    def __init__(self, hass, sonnenbatterie:sonnenbatterie, allSensorsPrefix, model_name, async_add_entities, mainCoordinator):     
        self.LOGGER = LOGGER
        self.LOGGER.info("SonnenBatteryReserve initialising with prefix "+allSensorsPrefix)
        self._unique_id= "{}{}".format(allSensorsPrefix,"battery_reserve") 
        self.entity_id= self._unique_id
        self.LOGGER.info("SonnenBatteryReserve id is "+self._unique_id)
        self._attr_has_entity_name = True
        self._name = "Battery Reserve"
        self.hass = hass
        self.sonnenbatterie = sonnenbatterie
        self.model_name = model_name
        self.mainCoordinator = mainCoordinator
        self._device_info = self.mainCoordinator.initialDeviceInfo
        self._attr_entity_config = EntityCategory.CONFIG
        self._attr_native_max_value = 100.0
        self._attr_native_min_value = 0.0
        self._attr_native_step = 1.0
        self._native_value = 0.0
        self._state = self._native_value
        self._enabled_by_default = True
        self._attr_device_class = NumberDeviceClass.BATTERY
        self._device_class = self._attr_device_class
        self._device_info = mainCoordinator.initialDeviceInfo
        self.state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:battery"
        self._coordinator = DataUpdateCoordinator(hass, LOGGER, name="Sonnen battery special sensors battery reserve mode", update_interval=timedelta(seconds=DEFAULT_UPDATE_FREQUENCY_BATTERY_RESERVE), update_method=self.async_handle_coordinator_update)
        super().__init__(self._coordinator)
        async_add_entities([self])
        self.LOGGER.info("SonnenBatteryReserve initialised")


        # register the services
        if not hass.services.has_service(DOMAIN, SERVICE_SET_BATTERY_RESERVE_ABSOLUTE) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_BATTERY_RESERVE_ABSOLUTE, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_battery_reserve_absolute),
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_ABSOLUTE): vol.All(
                          vol.Coerce(int), vol.Range(min=0, max=100)
                        )
                    }
                ),
            ) 
        self.LOGGER.info("SonnenBatteryReserve initialised added service "+SERVICE_SET_BATTERY_RESERVE_ABSOLUTE)

        if not hass.services.has_service(DOMAIN, SERVICE_SET_BATTERY_RESERVE_RELATIVE) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_BATTERY_RESERVE_RELATIVE, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_battery_reserve_relative),
            )
        self.LOGGER.info("SonnenBatteryReserve initialised added service "+SERVICE_SET_BATTERY_RESERVE_RELATIVE)

        if not hass.services.has_service(DOMAIN, SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_OFFSET) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_OFFSET, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_battery_reserve_relative_with_offset),
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_RELATIVE_OFFSET): vol.All(
                          vol.Coerce(int), vol.Range(min=-100, max=100)
                        )
                    }
                ),
            )
        self.LOGGER.info("SonnenBatteryReserve initialised added service "+SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_OFFSET)

        if not hass.services.has_service(DOMAIN, SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_MINIMUM) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_MINIMUM, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_battery_reserve_relative_with_minimum),
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_MINIMIM): vol.All(
                          vol.Coerce(int), vol.Range(min=0, max=100)
                        ),
                    }
                ),
            )
        self.LOGGER.info("SonnenBatteryReserve initialised added service "+SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_MINIMUM)

        if not hass.services.has_service(DOMAIN, SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_OFFSET_AND_MINIMUM) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_OFFSET_AND_MINIMUM, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_battery_reserve_relative_with_offset_and_minimum),
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_RELATIVE_OFFSET): vol.All(
                          vol.Coerce(int), vol.Range(min=-100, max=100)
                        ),
                        vol.Required(SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_MINIMIM): vol.All(
                          vol.Coerce(int), vol.Range(min=0, max=100)
                        ),
                    }
                ),
            )
        self.LOGGER.info("SonnenBatteryReserve initialised added service "+SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_OFFSET_AND_MINIMUM)

        if not hass.services.has_service(DOMAIN, SERVICE_GET_BATTERY_RESERVE_UPDATE_FREQUENCY) :
            hass.services.async_register(
                DOMAIN,
                SERVICE_GET_BATTERY_RESERVE_UPDATE_FREQUENCY, 
                verify_domain_control(hass, DOMAIN)(self.sonnenbatterie_set_battery_reserve_update_frequency),
                # we try and have voluptuous make the more lower case before checking it's in the list
                vol.Schema(
                    {
                        vol.Required(SERVICE_ATTR_GET_BATTERY_RESERVE_UPDATE_FREQUENCY): vol.All(
                            vol.Coerce(int), vol.Range(min=10, max=300),
                        )
                    }
                ),
            ) 
        self.LOGGER.debug("SonnenBatteryOperatingMode setup service "+SERVICE_GET_BATTERY_RESERVE_UPDATE_FREQUENCY)


        self.LOGGER.info("SonnenBatteryReserve initialised")



    def setUpdateInternal(self, updateIntervalInSeconds:int) :
        self._coordinator.update_interval = timedelta(seconds=updateIntervalInSeconds)
        self.LOGGER.info("SonnenBatteryReserve setUpdateInternal setting frequency "+(str(updateIntervalInSeconds)))

    async def sonnenbatterie_set_battery_reserve_update_frequency(self, call):
        self.LOGGER.debug("SonnenBatteryReserve sonnenbatterie_set_battery_reserve_update_frequency  starting")
        newFrequency = int(call.data[SERVICE_ATTR_GET_BATTERY_RESERVE_UPDATE_FREQUENCY])
        await self.hass.async_add_executor_job(self.setUpdateInternal, newFrequency)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._device_info
    
    # this is probabaly a horrendous and very non python / HA way to do things, but I had all 
    # sorts of errors around hass async execution and I just couldn't figure a solution out
    # other than this that didn't involve setting up a separate thread.
    def setter_absolute(self, new_reserve_absolute):
        try:
            self.sonnenbatterie.set_battery_reserve(new_reserve_absolute)
        except Exception as e:
            self.LOGGER.warn("SonnenBatteryReserve Unable to set absolute battery reserve, type "+str(type(e))+", details "+str(e))     
        # we may have changed it, update the state
        self.update_state()
        #self.schedule_update_ha_state()

    async def sonnenbatterie_set_battery_reserve_absolute(self, call):
        self.LOGGER.debug("SonnenBatteryReserve set reserve starting")
        new_reserve_absolute = int(call.data[SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_ABSOLUTE])
        self.LOGGER.info("SonnenBatteryReserve set reserve targeting "+str(new_reserve_absolute))
        await self.hass.async_add_executor_job(self.setter_absolute, new_reserve_absolute)

    def setter_relative(self, reserve_offset):
        try:
            self.sonnenbatterie.set_battery_reserve_relative_to_currentCharge(reserve_offset)
        except Exception as e:
            self.LOGGER.warn("SonnenBatteryReserve Unable to set relative battery reserve to offset "+str(reserve_offset)+", type "+str(type(e))+", details "+str(e))     
        # we may have changed it, update the state
        self.update_state()
        #self.schedule_update_ha_state()

    async def sonnenbatterie_set_battery_reserve_relative(self, call):
        self.LOGGER.info("SonnenBatteryReserve set reserve to current level starting")
        await self.hass.async_add_executor_job(self.setter_relative, 0)

    async def sonnenbatterie_set_battery_reserve_relative_with_offset(self, call):
        self.LOGGER.debug("SonnenBatteryReserve set reserve relative with offset starting")
        reserve_offset = int(call.data[SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_RELATIVE_OFFSET])
        self.LOGGER.info("SonnenBatteryReserve set reserve relative targeting offset "+str(reserve_offset))
        await self.hass.async_add_executor_job(self.setter_relative, reserve_offset)


    def setter_relative_with_minimum(self, offset, minimum_reserve):
        try:
            self.sonnenbatterie.set_battery_reserve_relative_to_currentCharge(offset, minimum_reserve)
        except Exception as e:
            LOGGER.warn("SonnenBatteryReserve Unable to set relative battery reserve to offset "+str(offset)+" with minimum "+str(minimum_reserve)+", type "+str(type(e))+", details "+str(e))     
        # we may have changed it, update the state
        self.update_state()
        #self.schedule_update_ha_state()

    async def sonnenbatterie_set_battery_reserve_relative_with_minimum(self, call):
        self.LOGGER.debug("SonnenBatteryReserve set reserve relative starting")
        minimum_reserve = int(call.data[SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_MINIMIM])
        self.LOGGER.info("SonnenBatteryReserve set reserve relative targeting with a minimum reserve of "+str(minimum_reserve))
        await self.hass.async_add_executor_job(self.setter_relative_with_minimum, 0, minimum_reserve)

    async def sonnenbatterie_set_battery_reserve_relative_with_offset_and_minimum(self, call):
        self.LOGGER.debug("SonnenBatteryReserve set reserve relative starting")
        offset = int(call.data[SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_RELATIVE_OFFSET])
        minimum_reserve = int(call.data[SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_MINIMIM])
        self.LOGGER.info("SonnenBatteryReserve set reserve relative targeting offset "+str(offset)+" with a ninimum reserve of "+str(minimum_reserve))
        await self.hass.async_add_executor_job(self.setter_relative_with_minimum, offset, minimum_reserve)

    def set_native_value(self, value: float) -> None:
        new_reserve_absolute = int(value)
        self.LOGGER.warn("SonnenBatteryReserve set_native_value reserve targeting "+str(new_reserve_absolute))
        self.setter_absolute(new_reserve_absolute)

    @callback
    async def async_handle_coordinator_update(self) -> None:
        await self.hass.async_add_executor_job(self.update_state)

    def update_state(self):
        """Handle updated data from the coordinator."""
        self.LOGGER.debug("SonnenBatteryReserve update state starting")
        try:
          newReserve = self.sonnenbatterie.get_battery_reserve()
          self._native_value = newReserve
          self._state = self._native_value
          self.LOGGER.debug("SonnenBatteryReserve update state retrieved reserve is "+str(newReserve))
          self.async_write_ha_state()
        except Exception as e:
            self.LOGGER.warn("SonnenBatteryReserve Unable to get battery reserve, type "+str(type(e))+", details "+str(e))         

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
    def should_poll(self):
        return False

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def entity_category(self):
        return EntityCategory.CONFIG
    
    @property
    def native_unit_of_measurement(self) -> str:
        return PERCENTAGE