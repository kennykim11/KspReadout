#include <LiquidCrystal.h>

// === SETTINGS ===
//
#define gaugeMin 100 //In Kelvin
#define gaugeMax 400 //In Kelvin
#define radiatorTogglePin 14 //A0 = 14
#define fuelTankTogglePin 15
#define extendControlPin 9
#define resendTimeout 1500 //In miliseconds
LiquidCrystal lcd(13, 12, 8, 7, 4, 2);
int gaugePins[4] = {11, 10, 5, 3};
int radExtendPins[4] = {16, 17, 18, 19}; //Red, Green, ...
String intro[4] = {"Actv Rad 1: ?", "Engine 1: ?", "Fuel Tank 1: ?", "Fuel Tnk Skn 1: ?"};
/* LCD SCREEN
______________________
|Radiator 1: 312 (59)|
|Engine 1: 312       |
|Fuel Tank 1: 312    |
|Fuel Tnk Skn 1: 312 |
----------------------
 */


// === CREATING CONSTANT VARIABLES ===
//Size of array = 1 + number of activeRadiators. First elements is which to display
int selectedRadiator, selectedEngine, selectedFuelTank;
int introLengths[4];
int gaugeRange, id, prevRadiatorToggle, prevFuelTankToggle;
String data;
bool gotKrpc = false;
int lastResend = 0;


void setup() {
  gaugeRange = (gaugeMax - gaugeMin);
  lcd.begin(20, 4); 
  Serial.begin(115200);
  Serial.setTimeout(5);
  setupLcd();
  //Setup Analog pins for output
  for (int i = 0; i < sizeof(radExtendPins); i++){
    pinMode(radExtendPins[i], OUTPUT);
  }
}



void loop() {
  if (!gotKrpc){
    //For responding to Arduino finding protocol run by computer
    if (Serial.available() > 0){
      if (Serial.readString() == "#"){
        Serial.println("!\0"); 
        gotKrpc = true;
        return;
      }
    }
  }

  else{
    //See any toggle has switched
    prevRadiatorToggle = selectedRadiator;
    prevFuelTankToggle = selectedFuelTank;
    selectedRadiator = getToggle(radiatorTogglePin);
    selectedFuelTank = getToggle(fuelTankTogglePin);
    if(prevRadiatorToggle != selectedRadiator || prevFuelTankToggle != selectedFuelTank){
      if (millis() > lastResend + resendTimeout){ //To not send a bunch of toggle commands over
        Serial.println("resend"); //Toggle switched so resend all data
      }
    }
  
    //Read from krpc
    if (Serial.available() > 0){
      String message = Serial.readString();
      id = message.substring(2,4).toInt();
      data = message.substring(4, message.length()-1); //to get rid of new line
      switch(message.substring(0,2).toInt()){
        case(2): //Temperature of Super CoolTemps
          analogWrite(gaugePins[id], (int) ((data.toInt()-gaugeMin) * 255/gaugeRange));
          break;
          
        case(3): //Whether radiator is extended (outputs 0 for retracted and 1 for extended)
          digitalWrite(radExtendPins[id*2], data.toInt() ^ 1); //Bitwise XOR with 1 makes it opposite
          digitalWrite(radExtendPins[id*2+1], data.toInt()); //HIGH == 1, LOW == 0 in Arduino.h
          break;
          
        case(4): //Temperature of active radiators
          if(selectedRadiator == id) printLcd(0, id, data);
          break;
          
        case(5): //Percent efficiency of active radiators
          if(selectedRadiator == id){
            lcd.setCursor(16, 0);
            if (data == "0") lcd.print("    "); //This happens if retracted and no percent is displayed
            else{
              lcd.print("(" + data + ")");
              if (data.length() < 1) lcd.print(" ");
            }
          }
          break;
          
        case(6): //Temperature of fuel tanks
          if(selectedFuelTank == id) printLcd(2, id, data);
          break;
          
        case(7): //Temperature of engines
          if(selectedFuelTank == id) printLcd(1, id, data);
          break;
          
        case(8): //Temperature of skins of fuel tanks
          if(selectedFuelTank == id) printLcd(3, id, data);
          break;
          
        default:
          break;
      }
    }
  
    
    //Get button press to toggle radiators
    if (digitalRead(9)){
      Serial.println("togRad" + String(selectedRadiator));
      delay(2000);
    }
  }
}

void setupLcd(){
  //Setup 4 rows of lcd screens
  for (int i = 0; i < 4; i++){
    lcd.setCursor(0,i);
    lcd.print(intro[i]);
    introLengths[i] = intro[i].length()-4;
  }
}

void printLcd(int row, int id, String message){
  //Given row and id, prints the value to the LCD
  lcd.setCursor(introLengths[row], row);
  lcd.print(String(id+1)+": "+ message + " ");
}


int getToggle(int pin){
  //Simply returns if on
  return analogRead(pin) > 512;
}
