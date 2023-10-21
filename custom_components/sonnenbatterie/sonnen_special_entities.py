import threading
from .const import *
from datetime import time, timedelta
from sonnenbatterie import sonnenbatterie
from .sonnen_battery_reserve import SonnenBatteryReserve
from .sonnen_battery_operating_mode import SonnenBatteryOperatingMode
from .sonnen_battery_tou_schedule import SonnenBatteryTOUSchedule
from .sonnen_operating_modes_map import SONNEN_BATTERY_TO_OPERATING_MODES, SONNEN_BATTERY_ALL_OPERATING_MODES
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

# this manages the async stuff, there is probabaly a way better mechanism to do this, but I don't know what it is
# I'm attempting here to make these attributes and the call backs separate for the remainfer of the ha_sonnenbatterie implementation
class SonnenSpecialEntities():
    def __init__(self, hass, sonnenbatterie:sonnenbatterie, async_add_entities, mainCoordinator):
        LOGGER.info("Starting SonnenSpecialEntities __init__ processing")
        self.hass = hass
        self.sonnenbatterie = sonnenbatterie
        self.async_add_entities = async_add_entities
        self.mainCoordinator = mainCoordinator
        self.sensors_configured = False
        self.stopped = threading.Event()
        LOGGER.info("Completed SonnenSpecialEntities __init__ processing")

    def start(self):
        LOGGER.info("Starting SonnenSpecialEntities waiting to initialise thread")
        threading.Thread(target=self.watcher).start()

    def stop(self):
        LOGGER.info("Stopping SonnenSpecialEntities waiting to initialise thread")
        self.stopped.set()
    
    def watcher(self) -> None:
        LOGGER.info("SonnenSpecialEntities starting watcher loop")
        while not self.stopped.isSet():
            try:
                # this will also mean that the model number will have been retrieved as that's done first
                prefix = self.mainCoordinator.allSensorsPrefix
                serial = self.mainCoordinator.serial
                LOGGER.warn("SonnenSpecialEntities watcher loop prefix is "+prefix)
                if (prefix == "") or (serial == ""):
                    LOGGER.warn("SonnenSpecialEntities in watcher processing mainCoordinator prefix or serial is not yet available, waiting")
                else:
                    LOGGER.warn("SonnenSpecialEntities in watcher processing, prefix is "+prefix)
                    self.configure_sensors(prefix)
                    # finished, lets break out of the loop
                    break
            except Exception as e:
                LOGGER.error("SonnenSpecialEntities in watcher processing mainCoordinator, type "+str(type(e))+", details "+str(e))
                
            LOGGER.warn("SonnenSpecialEntities in watcher about to wait")
            # hang around a bit, tbhis will be interrupted if the stop is called
            self.stopped.wait(5)
        LOGGER.debug("Completed the SonnenSpecialEntities startup loop")
        self.stop()

    def configure_sensors(self, prefix):
        LOGGER.warn("Configuring SonnenSpecialEntities sensors with prefix "+prefix)
        model_name=self.mainCoordinator.model_name
        self.sonnenbatteryreserve = SonnenBatteryReserve(self.hass, self.sonnenbatterie, prefix, model_name, self.async_add_entities, self.mainCoordinator)
        self.sonnenbatteryoperatingmode = SonnenBatteryOperatingMode(self.hass, self.sonnenbatterie, prefix, model_name, self.async_add_entities, self.mainCoordinator)
        self.sonnenbatterytouschedule = SonnenBatteryTOUSchedule(self.hass, self.sonnenbatterie, prefix, model_name, self.async_add_entities, self.mainCoordinator)

        
