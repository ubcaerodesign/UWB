import csv
import time
import serial

SERIAL_PORT = "COM3"
BAUD_RATE = 9600
DATA_SIZE = 5000  # Match C++ dataSize
ESTIMATED_DURATION = (
    DATA_SIZE * 4 * 0.015 + 10.0
)  # Scale timeout dynamically

HEADERS = ["x", "y", "Anchor Tag", "Calibration"]
for i in range(1, 8):
  HEADERS.extend([f"Tag {i} Dist", f"Tag {i} Err"])

try:
  with open("uwb_aerodesign_test.csv", "x", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(HEADERS)
except FileExistsError:
  pass


def drain_serial(ser):
  time.sleep(0.05)
  while ser.in_waiting > 0:
    ser.read(ser.in_waiting)


def check_connection(ser):
  print("Checking connection (sending AT)...")
  drain_serial(ser)
  ser.write(b"AT\r\n")
  ser.flush()

  timeout = time.time() + 2.0
  while time.time() < timeout:
    if ser.in_waiting > 0:
      line = ser.readline().decode("utf-8", errors="ignore").strip()
      print(f"Check resp: {line}")
      if "+OK" in line:
        return True
    time.sleep(0.05)
  return False


def reset_esp32(ser):
  print("Sending RESET ESP32 command...")
  ser.write(b"RESET ESP32\r\n")
  ser.flush()
  time.sleep(2.0)
  drain_serial(ser)


print(f"Connecting to ESP32 on {SERIAL_PORT}...")
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)
drain_serial(ser)

if not check_connection(ser):
  print("Initial AT check failed. Sending RESET ESP32...")
  reset_esp32(ser)
  if not check_connection(ser):
    print(
        "FAILURE: Connection validation failed after reset. ESP32 unresponsive."
    )
  else:
    print("Connection valid (+OK confirmed after reset).")
else:
  print("Connection valid (+OK confirmed).")

while True:
  print("\n--- NEW TEST CYCLE ---")
  try:
    x_input = float(input("Enter X coordinate (cm): "))
    y_input = float(input("Enter Y coordinate (cm): "))
  except ValueError:
    print("Invalid number input, skipping.")
    continue

  input("Press Enter to prompt ESP32 and start the test...")

  drain_serial(ser)
  ser.write(b"TEST\r\n")
  ser.flush()
  print(
      f"Test running... streaming 4 values per row (timeout:"
      f" {ESTIMATED_DURATION:.1f}s)."
  )

  test_start_time = time.time()
  test_data_received = False

  with open("uwb_aerodesign_test.csv", "a", newline="") as f:
    writer = csv.writer(f)

    row = [""] * len(HEADERS)
    row[0] = x_input
    row[1] = y_input
    batch_count = 0

    while time.time() - test_start_time < ESTIMATED_DURATION:
      if ser.in_waiting > 0:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        print(f"ESP32: {line}")

        if "Test Complete" in line:
          test_data_received = True
          if batch_count > 0:
            writer.writerow(row)
          break

        parts = line.split(",")
        if len(parts) >= 2:
          tag_id_str = parts[0].strip()
          try:
            dist = int(parts[1].strip())
            tag_idx = int(tag_id_str)
            if 1 <= tag_idx <= 7:
              col_index = 4 + (tag_idx - 1) * 2
              row[col_index] = dist
              batch_count += 1
              if batch_count == 4:
                writer.writerow(row)
                row = [""] * len(HEADERS)
                row[0] = x_input
                row[1] = y_input
                batch_count = 0
          except ValueError:
            pass
      time.sleep(0.005)

  if not test_data_received:
    print("WARNING: Test timed out. Draining stale serial buffer...")
    drain_esp32_residual = time.time()
    while time.time() - drain_esp32_residual < 3.0:
      if ser.in_waiting > 0:
        drain_serial(ser)
      time.sleep(0.1)

  print("Test Complete. 4-value bundled rows saved.")
  next_coords = input(
      "Press Enter to prompt for next coords (or type 'q' to quit): "
  )
  if next_coords.strip().lower() == "q":
    break

ser.close()
