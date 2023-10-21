### 230225

- split out 'battery_system' information (`ppv`, `ipv`, `upv`)into own sensors (thanks @TobyRh)

  WARNING: This is possibly a breaking change! If your setup doesn't provide values for `ppv`, `ipv`
  and `upv` under the inverter settings, those values are lost and can now be found under new names:
  | before | after |
  |---|---|
  | `inverter_ipv` | `battery_system_ipv` |
  | `inverter_ppv` | `battery_system_ppv` |
  | `inverter_upv` | `battery_system_upv` |

  You can check your system's settings using [this gist](https://gist.github.com/RustyDust/2dfdd9e9d0f3b5476b5e466203123f6f)
- make GitHub actions work again
  - fix ordering of keys in manifest.json
  - update to actions@v3

### 231021

Split the SonnenBatteriSensrot out to agoid having recursive imports
Added support for :
    Retrieval and setting (via servcies) the following :
         Operating mode (currently supporetas the modes supported but the 9.53 hybrid of Automatic, Manual and Time of Use. The battery 30% mode is supported but it's very unclear what that is) The servies let you chose the mode - see the sonnen_operating_mosed_map.py file for the list of modes and abbreviations supported. If the battery is not a known type then the code defaults to allowing all known modes (but the Servcies UI only supports Automatic, Manual and Time Of use). The operatine modes are specifiues in the python_sonnenbatteris imported module and the nicknames mappng sin the sonnen_operating_modes_map.py file.

         Battery reserve (the amount held in reserve in case of a power cut) which when in Automatic and time of use modes can also be used to trigger a battery charge (of the current level is below the reserve level will charge until the reserve is achieved). The battery rserve can be set in a number of ways as an absolute number, to the current level (so to stop discharging immediately), relative to the current level, but offset (e.g. current level +5%), to the current level but with a minimum level which is applied if the current leveel is less than the minimum, and to the current level with an offset and als a minimum (so take the current level, apply the offset and if less than the minimum use the minimum, otherwise the calculated offset from the current level) 

         Time of use schedule, this is a string and only supports a single schedule window in this version, If a TOU window is specified where the end time is "before" the start time (e.g. stat at 23:00, end ad 05:00) then the schedule is adjusted to that the end time is treated as if it was the following day (this is the way the Sonnen web ui on my 9.53 hybrid does things, in practice this would create a 23:00 - midnight and then a midnight to 0500 in this example) For the 9.53 at least you need to set a max power consumption for the entire building to prevent the crarging operation overloading the building supply. This is entered in KWh with a min of 5 and a max of 46 (as that is what the UI on my battery opffers as upper and lower limits, though in practice you may want to use a lower limit depending on your building electricity supply capabilties)

         To support folks who want to manually control the battery power flowes it's possible to set a flow rate, in theory (according to the API does this can be from -10000w to +10000w in practice the code will attempt to detect from the battery type and is currently limited to 3Kwh for a 9.53 and a default of 3Kwh for battery that's not a 9.53. Adding new battery types can done using the sonnen_flow_rates.py file