import logging
import voluptuous as vol
from datetime import timedelta
from homeassistant.helpers import config_validation as cv
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_IP_ADDRESS,
    CONF_SCAN_INTERVAL
)
LOGGER = logging.getLogger(__package__)

DOMAIN = "sonnenbatterie"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_REQUEST_TIMEOUT = 10

CONFIG_SCHEMA_A=vol.Schema(
            {
                vol.Required(CONF_USERNAME): vol.In(["User", "Installer"]),
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_IP_ADDRESS): str,
            }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: CONFIG_SCHEMA_A
    },
    extra=vol.ALLOW_EXTRA,
)

ATTR_SONNEN_DEBUG = "sonnenbatterie_debug"
DEFAULT_SONNEN_DEBUG = False
ATTR_REQUEST_TIMEOUT = "network_timeout_interval"

PLATFORMS = ["sensor"]
def flattenObj(prefix,seperator,obj):
    result={}
    for field in obj:
        val=obj[field]
        valprefix=prefix+seperator+field
        if type(val) is dict:
            sub=flattenObj(valprefix,seperator,val)
            result.update(sub)
        else:
            result[valprefix]=val
    return result


# how frequently to do the updates
DEFAULT_UPDATE_FREQUENCY_OPERATING_MODE=60
DEFAULT_UPDATE_FREQUENCY_BATTERY_RESERVE=60
DEFAULT_UPDATE_FREQUENCY_TOU_SCHEDULE=60

# list of the battery names we know of, the name is reported from the battery_system.system.model_name
SONNEN_MODEL_HYBRID_953_9010_ND_NAME='hyb 9.53 9010 ND'
SONNEN_MODEL_UNKNOWN_NAME="UNKNOWN"

# service definition stuff
# operating mdoe
SERVICE_SET_OPERATING_MODE="sonnen_set_battery_operating_mode"
SERVICE_ATTR_OPERATING_MODE_MODE="sonnen_battery_operating_mode"
SERVICE_GET_OPERATING_MODE_UPDATE_FREQUENCY="sonnen_get_operating_mode_update_frequency"
SERVICE_ATTR_GET_OPERATING_MODE_UPDATE_FREQUENCY="sonnen_battery_get_operating_mode_update_frequency"


# the flow rate to use when running in manual mode
SERVICE_SET_FLOW_RATE="sonnen_set_manual_flow_rate"
SERVICE_ATTR_FLOW_RATE="sonnen_battery_flow_rate"

# battery reserve management
SERVICE_SET_BATTERY_RESERVE_ABSOLUTE="sonnen_set_battery_reserve_absolute"
SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_ABSOLUTE="sonnen_battery_reserve_level_absolute"
SERVICE_SET_BATTERY_RESERVE_RELATIVE="sonnen_set_battery_reserve_relative"
SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_OFFSET="sonnen_set_battery_reserve_relative_with_offset"
SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_RELATIVE_OFFSET="sonnen_battery_reserve_level_relative_offset"
SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_MINIMUM="sonnen_set_battery_reserve_relative_with_minimum"
SERVICE_ATTR_SET_BATTERY_RESERVE_LEVEL_MINIMIM="sonnen_battery_reserve_level_minimum"
# this re-uses the offset and minimums from above
SERVICE_SET_BATTERY_RESERVE_RELATIVE_WITH_OFFSET_AND_MINIMUM="sonnen_set_battery_reserve_relative_with_offset_and_minimum"
SERVICE_GET_BATTERY_RESERVE_UPDATE_FREQUENCY="sonnen_get_battery_reserve_update_frequency"
SERVICE_ATTR_GET_BATTERY_RESERVE_UPDATE_FREQUENCY="sonnen_battery_get_battery_reserve_update_frequency"

# Time of use schedule
SERVICE_SET_TOU_SCHEDULE="sonnen_set_tou_schedule"
SERVICE_ATTR_TOU_START="tou_start"
SERVICE_ATTR_TOU_END="tou_end"
SERVICE_ATTR_TOU_MAX_POWER_IN_KW="tou_max_incomming_power_in_kw"
SERVICE_GET_TOU_UPDATE_FREQUENCY="sonnen_get_tou_update_frequency"
SERVICE_ATTR_GET_TOU_UPDATE_FREQUENCY="sonnen_battery_get_tou_update_frequency"

TOU_SCHEDULE_MAX_INCOMMING_POWER_IN_KW=100
TOU_SCHEDULE_MIN_INCOMMING_POWER_IN_KW=1

# these are used to define the names used to control the set operations
SETTING_MANAGER_BATTERY_RESERVE_NAME="SetBatteryReserve"
SETTING_MANAGER_OPERATING_MODE_NAME="SetOperatingMode"
SETTING_MANAGER_TIME_OF_USE_NAME="SetTOU"
SETTING_MANAGER_FLOW_RATE_NAME="SetFlowRate"