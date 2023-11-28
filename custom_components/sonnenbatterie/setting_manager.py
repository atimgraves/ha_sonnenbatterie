# this file helps maintain specific settings that have been requested, but may not have been applied for some reason
# (usualy network errors though occasionaally the battery just doesn't respond)
import requests
import threading
import traceback

from .const import LOGGER


class _SonnenSettingCommand():
    def __init__(self, hass, settingName:str, settingTargetLambda, retrieveValueLambda, testTargetAchievedLambda, postSetLambda, settingsManager , targetValue, retryInterval, retryCount, description):
        self._hass = hass
        self._settingName = settingName
        self._settingsManager = settingsManager
        self._stopped = threading.Event()
        self._running = False
        self._settingLock = threading.Lock()
        self.updateTarget(settingTargetLambda, retrieveValueLambda, testTargetAchievedLambda, postSetLambda, targetValue,  retryInterval, retryCount, description)

    def updateTarget(self, settingTargetLambda, retrieveValueLambda, testTargetAchievedLambda, postSetLambda, targetValue, retryInterval, retryCount, description):
        # make changes in the lock to encure that they don't come in part way through
        with self._settingLock:
            self._targetValue = targetValue
            self._targetValueStr = "Not provided"
            if (self._targetValue != None) :
                self._targetValueStr  = str(self._targetValue)
            self._settingTargetLambda = settingTargetLambda
            self._retrieveValueLambda = retrieveValueLambda
            self._retrieveValueLambdaStr = "Not set"
            if (self._retrieveValueLambda != None):
                self._retrieveValueLambdaStr = "Provided"
            self._testTargetAchievedLambda = testTargetAchievedLambda
            self._testTargetAchievedLambdaStr = "Not set"
            if (self._testTargetAchievedLambda != None):
                self._testTargetAchievedLambdaStr = "Provided"
            self._postSetLambda = postSetLambda
            self._postSetLambdaStr = "Not set"
            if (self._postSetLambda != None):
                self._postSetLambdaStr = "Provided"
            if (retryInterval < 0) :
                LOGGER.warn("SonnenSettingCommand for "+self._settingName+"  "+self._description+"  negative retry interval of "+str(retryInterval)+" was supplied. This is not allowed and will default to 60")
                retryInterval = 60
            self._retryInterval = retryInterval
            if (retryCount < 0) :
                LOGGER.warn("SonnenSettingCommand for "+self._settingName+" "+self._description+" negative retry cound of "+str(retryCount)+" was supplied. This is not allowed and will default to 10")
                retryCount = 10
            self._retryCount = retryCount
            self._origRetryCount = retryCount
            if (description == None) :
                self._description = "No description provided"
            else:
                self._description = description

    def describe(self) -> str:
        return "Setting "+self._settingName+" "+self._description+" to "+self._targetValueStr+" retrieve value lambda "+self._retrieveValueLambdaStr+" test target achieved lambda "+self._testTargetAchievedLambdaStr+ " post set lambda "+self._postSetLambdaStr+" retrying every "+str(self._retryInterval)+" seconds with "+str(self._retryCount)+" retried left out of the origional "+str(self._origRetryCount)

    async def start(self):
        with self._settingLock:
            if not self._running:
                LOGGER.debug("Starting SonnenSettingCommand thread for "+self._settingName+"  "+self._description)
                threading.Thread(target=self.watcher).start()
                self._running = True
                LOGGER.debug("Started SonnenSettingCommand thread for "+self._settingName+"  "+self._description)
            else:
                LOGGER.debug("SonnenSettingCommand thread already running for "+self._settingName+"  "+self._description)


    def stop(self):
        with self._settingLock:
            LOGGER.debug("Stopping SonnenSettingCommand waiting to initialise thread for "+self._settingName+"  "+self._description)
            self._stopped.set()
            self._running = False
    
    def watcher(self) -> None:
        LOGGER.info("SonnenSettingCommand starting setting "+self._settingName+"  "+self._description)
        # this is used to let us sleep outside the lock if there was a problem
        sleepOutsideLock = False
        while not self._stopped.isSet() and (self._retryCount != 0):
            # if there was a prvious problem then the loop will have continued and got to here
            # sleepOutsideLock will have been set so do the sleep
            # doing it this way allows for a change to be made while sleeping here and thus let this handle a changed value
            # this is needed to allow an incomming change to happen while we are blocked on a set or retrieve operation and the loop will then update
            if (sleepOutsideLock) :
                LOGGER.debug("SonnenSettingCommand doing sleep outside lock for problem")
                # must disable this incase we have a success later on
                sleepOutsideLock = False
                self._stopped.wait(self._retryInterval)

            with self._settingLock:
                LOGGER.debug("SonnenSettingCommand trying setting " +self._settingName+"  "+self._description+" attempts remaining"+str(self._retryCount))
                # decrement the retry if needed
                if (self._retryCount > 0) :
                    LOGGER.debug("The SonnenSettingCommand loop " +self._settingName+" starting iteration "+str(self._retryCount)+" out of the origional "+str(self._origRetryCount))
                    self._retryCount = self._retryCount -1 
                # try to set the value, if there is a ptroblem then setErrorMsg will be set for error handling
                setMsg = None
                setMsgError = False
                try:
                    self._settingTargetLambda()
                    LOGGER.debug("SonnenSettingCommand completed setting"+self._settingName+"  "+self._description)
                except requests.exceptions.Timeout as te:
                    setMsg = "SonnenSettingCommand Timeout getting data, iteration "+str(self._retryCount)+" out of the origional "+str(self._origRetryCount)+" "+str(type(te))+", details "+str(te)+" waiting to retry"
                except requests.exceptions.ConnectionError as ce:
                    setMsg = "SonnenSettingCommand ConnectionError getting data, iteration "+str(self._retryCount)+" out of the origional "+str(self._origRetryCount)+" "+str(type(ce))+", details "+str(ce)+" waiting to retry"
                except requests.exceptions.HTTPError as he:
                    setMsg="SonnenSettingCommand HTTPError getting data, iteration "+str(self._retryCount)+" out of the origional "+str(self._origRetryCount)+" "+str(type(e))+", details "+str(he)+" waiting to retry"
                except Exception as e:
                    setMsg = "SonnenSettingCommand error processing setting "+self._settingName+"  "+self._description+", type "+str(type(e))+", details "+str(e)+" traceback "+traceback.format_exc()+" waiting to retry"
                    setMsgError = True
                if setMsg != None:
                    if setMsgError:
                        LOGGER.error(setMsg)
                    else:
                        LOGGER.warn(setMsg)
                    # set the flag to do the sleep before re-entering the lock as we need to let other things have a chance
                    sleepOutsideLock = True
                    continue
                # to get here the settings command can't have thrown an error
                # if there is no target value set then nothing to check to see if it's worked so as there can;t havwe been an exception can exit
                if (self._targetValue == None):
                    LOGGER.info("Completed the SonnenSettingCommand command sucesfully with no target provided for setting "+self._settingName+"  "+self._description)
                    break

                if (self._retrieveValueLambda == None):
                    LOGGER.info("Completed the SonnenSettingCommand loop for setting "+self._settingName+"  "+self._description+" the check lambda ("+self._retrieveValueLambdaStr+") was not provided")            
                    break
                
                # check if the set gave us the right value
                retrievedValue = None
                retrieveMsg = None
                retrieveMsgError = False
                try:
                    LOGGER.debug("SonnenSettingCommand trying to retrieve data for testing "+self._settingName+"  "+self._description)     
                    retrievedValue = self._retrieveValueLambda ()  
                    LOGGER.debug("SonnenSettingCommand completed get retrieve data for testing "+self._settingName+"  "+self._description)   
                except requests.exceptions.Timeout as te:
                    retrieveMsg = "SonnenSettingCommand error getting retrieve data "+self._settingName+"  "+self._description+", type "+str(type(te))+", details "+str(te)+" waiting to retry"
                except requests.exceptions.ConnectionError as ce:
                    retrieveMsg = "SonnenSettingCommand error getting retrieve data "+self._settingName+"  "+self._description+", type "+str(type(ce))+", details "+str(ce)+" waiting to retry"
                except requests.exceptions.HTTPError as he:
                    retrieveMsg = "SonnenSettingCommand error getting retrieve data "+self._settingName+"  "+self._description+", type "+str(type(he))+", details "+str(he)+" waiting to retry"
                except Exception as e:
                    retrieveMsg = "SonnenSettingCommand error processing setting "+self._settingName+"  "+self._description+", type "+str(type(e))+", details "+str(e)+" traceback "+traceback.format_exc()+" waiting to retry"
                    retrieveMsgError = True

                if retrieveMsg != None:
                    if retrieveMsgError:
                        LOGGER.error(retrieveMsg)
                    else:
                        LOGGER.warn(retrieveMsg)
                    
                    # set the flag to do the sleep before re-entering the lock as we need to let other things have a chance
                    sleepOutsideLock = True
                    continue
            
                # to get here the set must have worked and the target value and retrieve lembds must not be None and must have worked
                # is a test lambda is not supploed then use the pythion equality check,
                # is the test lambda is supplied then 
                if (self._testTargetAchievedLambda == None):
                    LOGGER.debug("SonnenSettingCommand  setting"+self._settingName+"  "+self._description+" testing using the default equality test")
                    if (self._targetValue == retrievedValue) :
                        LOGGER.debug("SonnenSettingCommand setting"+self._settingName+"  "+self._description+" target value of "+str(self._targetValue)+" has been achieved (default equality test)")
                        break
                    else:
                        LOGGER.debug("SonnenSettingCommand problem processing setting"+self._settingName+"  "+self._description+" set failed, got :"+str(retrievedValue)+": which is type "+str(type(retrievedValue))+" back when expected :"+self._targetValueStr+": which is of type "+str(type(self._targetValueStr))+" (default equality test)")
                else :
                    LOGGER.debug("SonnenSettingCommand  setting"+self._settingName+"  "+self._description+" testing using supplied equality test")
                    try:
                        if (self._testTargetAchievedLambda(self._targetValue, retrievedValue)) :
                            LOGGER.debug("SonnenSettingCommand setting"+self._settingName+"  "+self._description+" target value of "+str(self._targetValueStr)+" has been achieved (supplied equality test)")
                            break
                        else:
                            LOGGER.debug("SonnenSettingCommand problem processing setting"+self._settingName+"  "+self._description+" set failed, got :"+str(retrievedValue)+": which is type "+str(type(retrievedValue))+" back when expected :"+self._targetValueStr+": which is of type "+str(type(self._targetValueStr))+" (supplied equality test)")
                    except Exception as et:
                        # This is likely a programming problem, we don't carry on because of that but do a diagnostic dump
                        LOGGER.error("SonnenSettingCommand error doing supplied equality test for "+self._settingName+"  "+self._description+" suoplied value :"+str(retrievedValue)+": which is type "+str(type(retrievedValue))+" against expected value :"+self._targetValueStr+": which is of type "+str(type(self._targetValueStr))+", exception details are type "+str(type(et))+", details "+str(et)+" traceback "+traceback.format_exc()+" will not retry or do any supplied post set lambda")
                        self._postSetLambda = None
                        break 
            
            # end of the with lock, do this sleep outside the lock
            # ensure that we won;t do a second sleep
            sleepOutsideLock = False
            # hang around a bit, this will be interrupted if the stop is called, then we will fail out in the while loop
            self._stopped.wait(self._retryInterval)
        # end of the while loop
        # if we ran out of retries then can;t do anything except yell for help
        if (self._retryCount == 0) :
                LOGGER.warn("The SonnenSettingCommand loop "+self.describe()+" has failed to complete, the setting has not ben applied")
        else :
            # the loop has terminated becsue we have got to the target, there was no target or check (but we sucesfully did the call) or we ran out of retries
            LOGGER.debug("SonnenSettingCommand loop "+self.describe()+" exited, tidying up")
            self.stop()
            if  (self._postSetLambda != None):
                # run any post set updates
                try:
                    self._postSetLambda()
                    LOGGER.debug("Completed the SonnenSettingCommand post set command for setting "+self._settingName+"  "+self._description+" to "+self._targetValueStr)
                except Exception as ue:
                    LOGGER.debug("SonnenSettingCommand error procedding updated notification for  "+self._settingName+"  "+self._description+", exception type "+str(type(ue))+", details "+str(ue)+" traceback "+traceback.format_exc())
            else:
                LOGGER.debug("Completed the SonnenSettingCommand post set command not provided for setting "+self._settingName+"  "+self._description+" to "+self._targetValueStr)
        # notify the manager that we're done, it will do it's thing to tidy up, this has top be done outside the lock as it re'enteres locked portions of this instance
        self._settingsManager.settingLoopCompleted(self._settingName)  
        return     

class SonnenSettingsManager():
    def __init__(self, hass):
        self._hass = hass
        self._settingsDictionary = {}
        self._managerLock = threading.Lock()

    # settingName - used to track what is being set and to change if modified in progress
    # settingTargetLambda - does the actuall set operation, much be supplpied
    # retrieveValueLambda - optional used to retrieve a value after the set for comparisson, if missing then the routines will only make sure that the set completes withoiuth and error
    # testTargetAchievedLambda - optional lambda that takes two arge and performane a comparisson to see if the setting has achieved the supplied target value, if missing then the python == operator is used
    # postSetLambda - optional if present executed once the equality tests have been com[p;leted, of if the retrieve and target value are missing then once a sucessfull set has been made
    # tarvetValue - an object to check against the value returned by the retrieveValueLambda (if present) is this or the retrieveValueLambda are missing then once the settingTargetLambda has been made withouth exception just completed
    # retriInterval - optional defaults to 60 seconds. In tghe event of a problem setting or the test for success fails then the code waits this number of seconds before retrying, if a negative number is supplied will default to 60
    # retryCount - optionsl number of tries to attempt to achieve sucess before giving up, a negative number  means to run the default count of 10 (but generates a warning) 0 means just do the post test and a postive number will count the loop down
    async def setDesiredSetting(self, settingName:str , settingTargetLambda, retrieveValueLambda=None, testTargetAchievedLambda=None, postSetLambda=None, targetValue=None, retryInterval:int=60, retryCount:int=10, description:str=None) :
        LOGGER.debug("SonnenSettingsManager setDesiredSettingCore pre lock aquire") 
        with self._managerLock:       
            LOGGER.debug("SonnenSettingsManager setDesiredSettingCore post lock aquire")  
            LOGGER.debug("SonnenSettingsManager keys before setDesiredSetting are "+str(self._settingsDictionary.keys()))
            # is there an instance running ? If so we update it with the new values
            setCommandInstance = self._settingsDictionary.get(settingName) 
            if setCommandInstance == None:
                LOGGER.debug("SonnenSettingsManager Creating new set for setting "+settingName) 
                #  Create the setting command instance
                setCommandInstance = _SonnenSettingCommand(self._hass, settingName, settingTargetLambda, retrieveValueLambda, testTargetAchievedLambda, postSetLambda, self , targetValue, retryInterval, retryCount, description)
                # have to save if BEFORE starting it in case it succedds in the setting before we save it
                self._settingsDictionary[settingName] = setCommandInstance 
                LOGGER.info("SonnenSettingsManager Created set of "+setCommandInstance.describe())
            else:
                LOGGER.debug("SonnenSettingsManager Updating previous set for "+setCommandInstance.describe())
                # just update it, no need to 
                setCommandInstance.updateTarget(settingTargetLambda, retrieveValueLambda, testTargetAchievedLambda, postSetLambda, targetValue, retryInterval, retryCount, description)
                LOGGER.info("SonnenSettingsManager Updated version is "+setCommandInstance.describe())

            LOGGER.debug("SonnenSettingsManager keys after setDesiredSetting are "+str(self._settingsDictionary.keys()))
        LOGGER.debug("SonnenSettingsManager setDesiredSettingCore lock released")  
        # start it processing
        LOGGER.debug("SonnenSettingsManager Starting loop for setting "+settingName) 
        await setCommandInstance.start()
    
    # for MT consistency any calles should make sure they have aquired the _managerLock 
    def _removeSetting(self, settingName)-> None:
        self._settingsDictionary.pop(settingName)

    # should only be called by the setting command to indicate it's finished and is stopping its own thread
    def settingLoopCompleted(self, settingName:str):
        LOGGER.debug("SonnenSettingsManager removing set command for "+settingName)
        with self._managerLock:
            LOGGER.debug("SonnenSettingsManager keys before settingLoopCompleted are "+str(self._settingsDictionary.keys()))
            setCmd = self._settingsDictionary.get(settingName)
            if setCmd  != None:       
                setCmd.stop()   
                self._removeSetting(settingName)
                LOGGER.debug("SonnenSettingsManager removed set command for "+settingName+" from dictionary")
            else :
                LOGGER.debug("SonnenSettingsManager no set command for "+settingName+" in dictionary")
            
            LOGGER.debug("SonnenSettingsManager keys after settingLoopCompleted are "+str(self._settingsDictionary.keys()))
        LOGGER.debug("SonnenSettingsManager removing set command for "+settingName+" from dictionary lock released")


    # just a convenience method to help with future changes may do something different later on
    def settingLoopAbandon(self, settingName:str):
        self.settingLoopCompleted(settingName)

    def _dumpSettingsDictKeys(self) -> str:
        resp = None
        for key in self._settingsMap.keys():
            if (resp == None):
                resp = key
            else:
                resp = resp + ", "+key
        
        if (resp == None):
            resp = ""
        return resp