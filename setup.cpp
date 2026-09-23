#include <Arduino.h>
#include <math.h>

const String anchorNum = "01"; //module numeber 01-07

const String tagNum1 = "03"; //module numeber 01-07
const String tagNum2 = "02"; //module numeber 01-07
const String tagNum3 = "03"; //module numeber 01-07
const String tagNum4 = "05"; //module numeber 01-07

const int Cal1 = -44;
const int Cal2 = -59;
const int Cal3 = -41;
const int Cal4 = -53;

const int trueDistance = 13; //distance in cm
const int dataSize = 1000;

const int RXp2 = 16;
const int TXp2 = 17;
const int NRST = 22;

void SetupAnchor();
void SetupTag();
float calculateSD(int data[], int size);
void ResetESP32();
void Test();

void setup() {
  pinMode(NRST, OUTPUT);
  digitalWrite(NRST, LOW);
  delay(100);
  digitalWrite(NRST, HIGH);
  delay(500);

  Serial.begin(9600);
  Serial2.begin(115200, SERIAL_8N1, RXp2, TXp2);
  Serial2.setTimeout(70);

  Serial.printf("Sent:");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n'); 
    command.trim();
    
    if (command == "SETUP ANCHOR"){
      SetupAnchor();
    }
    else if (command == "SETUP TAG"){
      SetupTag();
    }
    else if (command == "RESET ESP32"){
      ResetESP32();
    }
    else if (command == "TEST"){
      Test();
    }
    else if (command.length() > 0) {
      Serial2.print(command);
      Serial2.print("\r\n");
    }
  }
  
  if (Serial2.available() > 0) {
    String response = Serial2.readString();
    Serial.print("Received: ");
    Serial.println(response);
    Serial.printf("Sent:");
  }
}

void SetupTag(){
  Serial.print("Setting up tag...\n");

  Serial2.print("AT+FACTORY\r\n");
  delay(200);
  Serial2.print("AT+NETWORKID=UBCAERO\r\n");
  delay(200);
  Serial2.print("AT+CPIN=9c5180f88c745ae937c1598352912a95\r\n");
  delay(200);
  Serial2.print("AT+ADDRESS=DESIGN" + tagNum1 + "\r\n");
  delay(200);

  Serial.print("Set up complete\n");
}

void SetupAnchor(){
  Serial.print("Setting up anchor...\n");

  Serial2.print("AT+FACTORY\r\n");
  delay(200);
  Serial2.print("AT+NETWORKID=UBCAERO\r\n");
  delay(200);
  Serial2.print("AT+CPIN=9c5180f88c745ae937c1598352912a95\r\n");
  delay(200);
  Serial2.print("AT+ADDRESS=DESIGN" + anchorNum + "\r\n");
  delay(200);
  Serial2.print("AT+MODE=1\r\n");
  delay(200);
  Serial.print("Calibrating\n");

  int data[dataSize];
  int misfire = 0;
  
  Serial2.print("AT+CAL=+50\r\n");

  for (int i = 0; i < dataSize; i++) {
    while(Serial2.available()) Serial2.read();

    String command = "AT+ANCHOR_SEND=DESIGN" + tagNum1 + ",4,TEST";
    Serial2.print(command + "\r\n");

    unsigned long startTime = millis();
    while (Serial2.available() == 0 && millis() - startTime < 1000) {
      delay(10);
    }

    if (Serial2.available() > 0) {
      String response = Serial2.readString();
      
      if (response.indexOf("+ANCHOR_RCV=") != -1) {
        int lastComma = response.lastIndexOf(',');
        int cmIndex = response.indexOf(" cm");

        if (lastComma != -1 && cmIndex != -1) {
          String numStr = response.substring(lastComma + 1, cmIndex);
          int datapoint = numStr.toInt();
          data[i] = datapoint;
          Serial.printf("Data Point %d: %d\n",i+1, datapoint - 50); 
        } else {
          i = i - 1;
        }
      } else {
        i = i - 1; 
        misfire = misfire + 1;
        Serial.print(response);
        delay(100);
      }
    } else {
      i = i - 1;
      misfire = misfire + 1;
    }
  }

  int sum = 0;
  for (int i = 0; i < dataSize; i++) {
    sum = sum + data[i];
  }

  int avg = sum / dataSize;
  int calNum = trueDistance - avg + 50;
  float sd = calculateSD(data, dataSize);
  
  Serial2.printf("AT+CAL=%d\r\n", calNum);
  Serial.printf("Calibration Adjustment: %d\n", calNum);
  Serial.printf("Standard Deviation: %f\n", sd);
  Serial.printf("Misfires: %d\n", misfire-1);

  return;
}

float calculateSD(int *data, int size) { 
  float sum = 0.0, mean, standardDeviation = 0.0;
  int i;

  for(i = 0; i < size; ++i) { 
    sum += data[i];
  }

  mean = sum / size; 

  for(i = 0; i < size; ++i) { 
    standardDeviation += pow(data[i] - mean, 2);
  }

  return sqrt(standardDeviation / size); 
}

void ResetESP32(){
  digitalWrite(NRST, LOW);
  delay(100);
  digitalWrite(NRST, HIGH);
  delay(500);
  Serial.printf("Reset Complete\nSent:");
}

void Test(){

  Serial2.print("AT+CAL=+50\r\n");

  // 1. Group the tags into an array for sequential polling
  String tags[4] = {tagNum1, tagNum2, tagNum3, tagNum4};
  int cal[4] = {Cal1, Cal2, Cal3, Cal4};

  for (int i = 0; i < dataSize; i++) {
    
    // 2. Inner loop iterates through each of the 4 tags
    for (int t = 0; t < 4; t++) {
      
      while(Serial2.available()) Serial2.read();

      String command = "AT+ANCHOR_SEND=DESIGN" + tags[t] + ",4,TEST";
      Serial2.print(command + "\r\n");

      unsigned long startTime = millis();
      while (Serial2.available() == 0 && millis() - startTime < 1000) {
        delay(2); // Reduced from 10 for faster serial polling
      }

      if (Serial2.available() > 0) {
        String response = Serial2.readString();
      
        if (response.indexOf("+ANCHOR_RCV=") != -1) {
          int lastComma = response.lastIndexOf(',');
          int cmIndex = response.indexOf(" cm");

          if (lastComma != -1 && cmIndex != -1) {
            String numStr = response.substring(lastComma + 1, cmIndex);
            int datapoint = numStr.toInt();
            
            // 3. Print in strict CSV format (e.g., "07,125") for Python/Excel
            // Note: .c_str() is required to print Arduino Strings with %s
            Serial.printf("%s,%d\n", tags[t].c_str(), max(datapoint + cal[t], 0)); 
          } 
          else {
            t = t - 1; // String malformed, retry this specific tag
          }
        } 
        else {
          t = t - 1; // Error received, retry this specific tag
          Serial.print(response);
          delay(10); 
        }
      } 
      else {
        t = t - 1; // Timeout occurred, retry this specific tag
      }
    }
  }
  Serial.print("Test Complete");
  return;
}
