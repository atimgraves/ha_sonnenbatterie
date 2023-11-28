import threading
import traceback
from .const import *
from datetime import time, timedelta
from .setting_manager import SonnenSettingsManager
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
        self.settingManager = SonnenSettingsManager(hass)
        LOGGER.info("Completed SonnenSpecialEntities __init__ processing")

    async def start(self):
        LOGGER.info("Starting SonnenSpecialEntities waiting to initialise thread")
        threading.Thread(target=self.watcher).start()

    def stop(self):
        LOGGER.info("Stopping SonnenSpecialEntities waiting to initialise thread")
        self.stopped.set()
    
    def watcher(self) -> None:
        # there seem to ba a whole bunch of potential race conditopona that may mean we don;t get everythign needed in the main coordinator
        # so here we do a bunch of sanity checks to make sure it's all OK before carrying on
        LOGGER.info("SonnenSpecialEntities starting watcher loop")
        while not self.stopped.isSet():
            try:
                # Check that the coordinator has got some of the initial data we need
                # this will also mean that the model number will have been retrieved as that's done first
                prefix = self.mainCoordinator.allSensorsPrefix
                serial = self.mainCoordinator.serial
                savedDeviceInfo = self.mainCoordinator.savedDeviceInfo
                deviceName = self.mainCoordinator.deviceName
                LOGGER.warn("SonnenSpecialEntities watcher loop prefix is "+prefix)
                if (prefix == "") or (serial == "") or (deviceName == "") or (savedDeviceInfo == None):
                    LOGGER.warn("SonnenSpecialEntities in watcher processing mainCoordinator prefix, serial, deviceName or savedDeviceInfo is not yet available, waiting")
                else:
                    LOGGER.warn("SonnenSpecialEntities in watcher processing, prefix is "+prefix)
                    dictSavedDeviceInfo = dict(savedDeviceInfo)
                    LOGGER.warn("SonnenSpecialEntities savedDeviceInfo is "+str(dictSavedDeviceInfo))
                    # examine the retrieved device info to make sure it's complete, if any of the model, name or sw_version are unknown then loop round again
                    incompleteDeviceInfo = False

                    if (dictSavedDeviceInfo.get("model") == None):
                        LOGGER.warn("SonnenSpecialEntities savedDeviceInfo model is None ")
                        incompleteDeviceInfo = True
                    if (dictSavedDeviceInfo.get("model") == "unknown"):
                        LOGGER.warn("SonnenSpecialEntities savedDeviceInfo model is unknown ")
                        incompleteDeviceInfo = True
                    if (dictSavedDeviceInfo.get("name") == None):
                        LOGGER.warn("SonnenSpecialEntities savedDeviceInfo name is None ")
                        incompleteDeviceInfo = True
                    if (dictSavedDeviceInfo.get("name") == "unknown"):
                        LOGGER.warn("SonnenSpecialEntities savedDeviceInfo name is unknown ")
                        incompleteDeviceInfo = True
                    if (dictSavedDeviceInfo.get("sw_version") == None):
                        LOGGER.warn("SonnenSpecialEntities sw_version name is None ")
                        incompleteDeviceInfo = True
                    if (dictSavedDeviceInfo.get("sw_version") == "unknown"):
                        LOGGER.warn("SonnenSpecialEntities sw_version name is unknown ")
                        incompleteDeviceInfo = True
                    if (incompleteDeviceInfo):
                        LOGGER.warn("SonnenSpecialEntities savedDeviceInfo missing core data, continuing")
                    else:
                        self.configure_sensors(prefix, savedDeviceInfo, deviceName)
                        # finished, lets break out of the loop
                        break    
            except Exception as e:
                LOGGER.error("SonnenSpecialEntities in watcher processing mainCoordinator, type "+str(type(e))+", details "+str(e)+" traceback "+traceback.format_exc())
                
            LOGGER.warn("SonnenSpecialEntities in watcher about to wait")
            # hang around a bit, tbhis will be interrupted if the stop is called
            self.stopped.wait(5)
        LOGGER.debug("Completed the SonnenSpecialEntities startup loop")
        self.stop()

    def configure_sensors(self, prefix, savedDeviceInfo, deviceName):
        # there seems to be some form of race condition
        LOGGER.warn("Configuring SonnenSpecialEntities sensors with prefix "+prefix)
        model_name=self.mainCoordinator.model_name
        self.sonnenbatteryreserve = SonnenBatteryReserve(self.hass, self.sonnenbatterie, prefix, model_name, self.async_add_entities, self.mainCoordinator, savedDeviceInfo, deviceName, self.settingManager)
        self.sonnenbatteryoperatingmode = SonnenBatteryOperatingMode(self.hass, self.sonnenbatterie, prefix, model_name, self.async_add_entities, self.mainCoordinator, savedDeviceInfo, deviceName, self.settingManager)
        self.sonnenbatterytouschedule = SonnenBatteryTOUSchedule(self.hass, self.sonnenbatterie, prefix, model_name, self.async_add_entities, self.mainCoordinator,savedDeviceInfo, deviceName, self.settingManager)

        
