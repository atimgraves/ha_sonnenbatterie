from homeassistant.components.sensor import (
    SensorEntity
)
from homeassistant.helpers.entity import DeviceInfo

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import LOGGER
class SonnenBatterieSensor(CoordinatorEntity,SensorEntity):
    def __init__(self,id,deviceinfo,coordinator,name=None):
        self._attributes = {}
        self._state = "0"
        self._deviceinfo=deviceinfo
        self.coordinator=coordinator
        self.entity_id = id
        if name is None:
            name = id
        self._name = name
        super().__init__(coordinator)
        LOGGER.info("Create Sensor {0}".format(id))

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self._deviceinfo
        


    def set_state(self, state):
        """Set the state."""
        if self._state==state:
            return
        self._state = state
        if self.hass is None:
            LOGGER.warning("hass not set, sensor: {} ".format(self.name))
            return
        self.schedule_update_ha_state()
        #try:
        #self.schedule_update_ha_state()
        #except:
        #    LOGGER.error("Failing sensor: {} ".format(self.name))

    def set_attributes(self, attributes):
        """Set the state attributes."""
        self._attributes = attributes

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return self.entity_id

    @property
    def should_poll(self):
        """Only poll to update phonebook, if defined."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    def update(self):
        LOGGER.info("update " + self.entity_id)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._attributes.get("unit_of_measurement", None)

    @property
    def device_class(self):
        """Return the device_class."""
        return self._attributes.get("device_class", None)

    @property
    def state_class(self):
        """Return the unit of measurement."""
        return self._attributes.get("state_class", None)
