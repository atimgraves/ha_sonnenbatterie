# this file helps maintain specific settings that have been requested, but may not have been applied for some reason
# (usualy network errors though occasionaally the battery just doesn't respond)
import requests
import threading
import traceback

from .const import LOGGER


class _SonnenSettingCommand():
    def __init__(self, hass, settingName:str, settingTargetLambda, checkTargetLambda, postSetLambda, settingsManager , targetValue, retryInterval, retryCount):
        self._hass = hass
        self._settingName = settingName
        self._settingsManager = settingsManager
        self._stopped = threading.Event()
        self._running = False
        self._settingLock = threading.Lock()
        self.updateTarget(settingTargetLambda, checkTargetLambda, postSetLambda, targetValue,  retryInterval, retryCount)

    def updateTarget(self, settingTargetLambda, checkTargetLambda, postSetLambda, targetValue, retryInterval, retryCount):
        # make changes in the lock to encure that they don't come in part way through
        with self._settingLock:
            self._targetValue = targetValue
            self._settingTargetLambda = settingTargetLambda
            self._checkTargetLambda = checkTargetLambda
            self._checkTargetLambdaStr = "Not set"
            if (self._checkTargetLambda != None):
                self._checkTargetLambdaStr = "Provided"
            self._postSetLambda = postSetLambda
            self._postSetLambdaStr = "Not set"
            if (self._postSetLambda != None):
                self._postSetLambdaStr = "Provided"
            self._retryInterval = retryInterval
            self._retryCount = retryCount
            self._origRetryCount = retryCount
            self._targetValueStr = "Not provided"
            if (self._targetValue != None) :
                self._targetValueStr  = str(self._targetValue)

    def describe(self) -> str:
        return "Setting "+self._settingName+" to "+self._targetValueStr+" check target lambds "+self._checkTargetLambdaStr+ " post set lambda "+self._postSetLambdaStr+" retrying every "+str(self._retryInterval)+" seconds with "+str(self._retryCount)+" retried left out of the origional "+str(self._origRetryCount)

    async def start(self):
        with self._settingLock:
            if not self._running:
                LOGGER.info("Starting SonnenSettingCommand waiting to initialise thread for "+self._settingName)
                threading.Thread(target=self.watcher).start()
                self._running = True
                LOGGER.info("Started SonnenSettingCommand thread for "+self._settingName)
            else:
                LOGGER.info("SonnenSettingCommand thread already running for "+self._settingName)


    def stop(self):
        with self._settingLock:
            LOGGER.info("Stopping SonnenSettingCommand waiting to initialise thread for "+self._settingName)
            self._stopped.set()
            self._running = False
    
    def watcher(self) -> None:
        LOGGER.info("SonnenSettingCommand starting setting "+self._settingName)
        while not self._stopped.isSet() and (self._retryCount != 0):
            with self._settingLock:
                LOGGER.warn("SonnenSettingCommand trying setting" +self._settingName+" attempts remaining"+str(self._retryCount))
                # decrement the retry if needed
                if (self._retryCount > 0) :
                    LOGGER.warn("The SonnenSettingCommand loop starting iteration "+str(self._retryCount)+" out of the origional "+str(self._origRetryCount))
                    self._retryCount = self._retryCount -1 
                # try to set the value
                try:
                    self._settingTargetLambda()
                    LOGGER.warn("SonnenSettingCommand completed setting"+self._settingName)
                except requests.exceptions.Timeout as e:
                    LOGGER.error("SonnenSettingCommand Timeout getting data iteration "+str(self._retryCount)+" out of the origional "+str(self._origRetryCount)+" "+str(type(e))+", details "+str(e)+" waiting to retry")
                    self._stopped.wait(self._retryInterval)  
                    continue  
                except Exception as e:
                    LOGGER.error("SonnenSettingCommand error processing setting "+self._settingName+", type "+str(type(e))+", details "+str(e)+" traceback "+traceback.format_exc()+" waiting to retry")
                    self._stopped.wait(self._retryInterval)
                    continue
                
                # to get here the settings command can't have thrown an error
                # if there is no target value set then nothing to check to see if it's worked so as there can;t havwe been an exception can exit
                if (self._targetValue == None):
                    LOGGER.warn("Completed the SonnenSettingCommand command sucesfully with no target provided for setting "+self._settingName)
                    break

                if (self._checkTargetLambda == None):
                    LOGGER.warn("Completed the SonnenSettingCommand loop for setting "+self._settingName+" the check lambda ("+self._checkTargetLambdaStr+") was not provided")            
                    break
                
                # check if the set gave us the right value
                updatedValue = None
                if (self._checkTargetLambda != None):
                    try:
                        LOGGER.warn("SonnenSettingCommand trying to get check data for setting"+self._settingName)     
                        updatedValue = self._checkTargetLambda ()  
                        LOGGER.warn("SonnenSettingCommand completed get check data for setting"+self._settingName)          
                    except requests.exceptions.Timeout as e:
                        LOGGER.error("SonnenSettingCommand Timeout getting check data iteration "+str(self._retryCount)+" out of the origional "+str(self._origRetryCount)+" "+str(type(e))+", details "+str(e)+" waiting to retry")
                        self._stopped.wait(self._retryInterval)  
                        continue  
                    except Exception as e:
                        LOGGER.error("SonnenSettingCommand error getting check data "+self._settingName+", type "+str(type(e))+", details "+str(e)+" traceback "+traceback.format_exc()+" waiting to retry")
                        self._stopped.wait(self._retryInterval)
                        continue
                else:
                    LOGGER.warn("SonnenSettingCommand no check lambda("+self._checkTargetLambdaStr+") to check for setting"+self._settingName)            
            
                # to get here the set must have worked and the target value and check must not be None and must have worked
                if (self._targetValue == updatedValue) :
                    LOGGER.warn("SonnenSettingCommand setting"+self._settingName+" target value of "+self._targetValue+" has been achieved")
                    break
                else:
                    LOGGER.warn("SonnenSettingCommand problem processing setting"+self._settingName+" set failed, got "+str(updatedValue)+" back when expected "+self._targetValueStr)
                # hang around a bit, this will be interrupted if the stop is called, then we will fail out in the while loop
                self._stopped.wait(self._retryInterval)
            # end of the with lock
        # end of the while loop

        # the loop has terminated becsue we have got to the target, there was no target or check (but we sucesfully did the call) or we ran out of retries
        LOGGER.info("SonnenSettingCommand loop exited, tidying up")
        self.stop()
        if  (self._postSetLambda != None):
            # run any post set updates
            try:
                self._postSetLambda()
                LOGGER.info("Completed the SonnenSettingCommand post set command for setting "+self._settingName+" to "+self._targetValueStr)
            except Exception as ue:
                LOGGER.error("SonnenSettingCommand error procedding updated notification for  "+self._settingName+", exception type "+str(type(ue))+", details "+str(ue)+" traceback "+traceback.format_exc())
        else:
            LOGGER.info("Completed the SonnenSettingCommand post set command not provided for setting "+self._settingName+" to "+self._targetValueStr)
        # notify the manager that we're done, it will do it's thing to tidy up, this has top be done outside the lock as it re'enteres locked portions of this instance
        self._settingsManager.settingLoopCompleted(self._settingName)  
        return     

class SonnenSettingsManager():
    def __init__(self, hass):
        self._hass = hass
        self._settingsMap = {}
        self._managerLock = threading.Lock()

    def setDesiredSettingHold(self, settingName:str , settingTargetLambda, checkTargetLambda=None, postSetLambda=None, targetValue=None, retryInterval:int=60, retryCount:int=60) :
        LOGGER.warn("SonnenSettingsManager setDesiredSetting start")
        self.setDesiredSettingCore(settingName , settingTargetLambda, checkTargetLambda, postSetLambda, targetValue, retryInterval, retryCount)
        LOGGER.warn("SonnenSettingsManager setDesiredSetting finished")

    async def setDesiredSetting(self, settingName:str , settingTargetLambda, checkTargetLambda=None, postSetLambda=None, targetValue=None, retryInterval:int=60, retryCount:int=60) :
        LOGGER.debug("SonnenSettingsManager setDesiredSettingCore pre lock aquire") 
        with self._managerLock:       
            LOGGER.debug("SonnenSettingsManager setDesiredSettingCore post lock aquire")  
            # is there an instance running ? If so we update it with the new values
            setCommandInstance = self._settingsMap.get(settingName) 
            if setCommandInstance == None:
                LOGGER.warn("SonnenSettingsManager Creating new set for setting "+settingName) 
                #  Create the setting command instance
                setCommandInstance = _SonnenSettingCommand(self._hass, settingName, settingTargetLambda, checkTargetLambda, postSetLambda, self , targetValue, retryInterval, retryCount)
                # have to save if BEFORE starting it in case it succedds in the setting before we save it
                self._settingsMap[settingName] = setCommandInstance 
                LOGGER.warn("SonnenSettingsManager Created set of "+setCommandInstance.describe())
                #self._hass.async_create_task(setCommandInstance.start())
                LOGGER.warn("SonnenSettingsManager Started loop for setting "+settingName) 
            else:
                LOGGER.warn("SonnenSettingsManager Updating previous set for "+setCommandInstance.describe())
                # just update it, no need to 
                setCommandInstance.updateTarget(settingTargetLambda, checkTargetLambda, postSetLambda, targetValue, retryInterval, retryCount)
                LOGGER.warn("SonnenSettingsManager Updated version is "+setCommandInstance.describe())
        #self._managerLock.release
        LOGGER.debug("SonnenSettingsManager setDesiredSettingCore lock released")  
        # start it processing
        await setCommandInstance.start()
    
    # for MT consistency any calles should make sure they have aquired the _managerLock 
    def _removeSetting(self, settingName)-> None:
        self._settingsMap.pop(settingName)

    # should only be called by the setting command to indicate it's finished and is stopping its own thread
    def settingLoopCompleted(self, settingName:str):
        LOGGER.debug("SonnenSettingsManager removing set command for "+settingName)
        with self._managerLock:
            setCmd = self._settingsMap.get(settingName)
            if setCmd  != None:       
                setCmd.stop()   
                self._removeSetting(settingName)
                LOGGER.debug("SonnenSettingsManager removed set command for "+settingName+" from dictionary")
            else :
                LOGGER.debug("SonnenSettingsManager no set command for "+settingName+" in dictionary")
        #self._managerLock.release()
        LOGGER.debug("SonnenSettingsManager removing set command for "+settingName+" from dictionary lock released")


    # just a convenience method to help with future changes may do something different later on
    def settingLoopAbandon(self, settingName:str):
        self.settingLoopCompleted(settingName)