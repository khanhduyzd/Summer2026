import serial
import time
import json
import urllib.request
import urllib.error
from datetime import datetime

# -----------------------------
# Serial / radio settings
# -----------------------------
SERIAL_PORT = "/dev/serial0"
BAUD_RATE = 9600

# -----------------------------
# API settings
# -----------------------------
API_KEY = "GardenSecret2026"

PEDESTRIAN_API_URL = "https://faridfarahmand.net/CEI/api_pedestrian.php"
SURVEY_API_URL = "https://faridfarahmand.net/CEI/api_survey.php"

# -----------------------------
# Acknowledgement password
# This is sent back after a valid message is received
# -----------------------------
ACK_PASSWORD = "LED"

def parse_combined_message(raw_message):
    """
    Expected message format:

        Gate_01, 09, A, B, C, D, E

    Example:

        Gate_01, 09, 1, 2, 3, 4, 5

    Meaning:

        node_id = Gate_01
        pedestrian_count = 09
        a = 1
        b = 2
        c = 3
        d = 4
        e = 5

    Also accepts Meshtastic-style prefix:

        fd60: Gate_01, 09, 1, 2, 3, 4, 5
    """
    raw_message = raw_message.strip()
    raw_message = raw_message.replace("\x00", "")

    # Remove optional Meshtastic prefix.
    # Example:
    # "fd60: Gate_01, 09, 1, 2, 3, 4, 5"
    # becomes:
    # "Gate_01, 09, 1, 2, 3, 4, 5"
    if ":" in raw_message:
        raw_message = raw_message.split(":", 1)[1].strip()

    parts = [part.strip() for part in raw_message.split(",")]

    if len(parts) != 7:
        raise ValueError(
            "Message must have 7 fields: node_id, pedestrian_count, a, b, c, d, e"
        )

    node_id = parts[0]

    if not node_id:
        raise ValueError("node_id is empty")

    try:
        pedestrian_count = int(parts[1])
        a = int(parts[2])
        b = int(parts[3])
        c = int(parts[4])
        d = int(parts[5])
        e = int(parts[6])
    except ValueError:
        raise ValueError("pedestrian_count and survey option counts must be integers")

    return node_id, pedestrian_count, a, b, c, d, e


def send_acknowledgement(serial_connection):
    """
    Sends only the secret ACK password back to the transmitter.
    """

    serial_connection.write((ACK_PASSWORD + "\n").encode("utf-8"))
    serial_connection.flush()

    print(f"ACK password sent")
def post_json(api_url, payload):
    """
    Sends JSON data to one API endpoint.
    """

    json_data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        api_url,
        data=json_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status_code = response.status
            response_body = response.read().decode("utf-8", errors="replace")

            if 200 <= status_code < 300:
                return True, status_code, response_body
            else:
               return False, status_code, response_body

    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        return False, error.code, response_body

    except urllib.error.URLError as error:
        return False, None, str(error)

def upload_pedestrian_count(node_id, pedestrian_count):
    """
    Uploads pedestrian count.

    JSON format:
        {
            "node_id": "Gate_01",
            "count": 9
        }
    """

    payload = {
        "node_id": node_id,
        "count": pedestrian_count
    }
    return post_json(PEDESTRIAN_API_URL, payload)


def upload_survey_counts(node_id, a, b, c, d, e):
    """
    Uploads survey option counts.
    JSON format:
        {
            "node_id": "Gate_01",
            "a": 1,
            "b": 2,
            "c": 3,
            "d": 4,
            "e": 5
        }
    """
    payload = {
        "node_id": node_id,
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "e": e
    }

    return post_json(SURVEY_API_URL, payload)
def process_message(serial_connection, raw_message):
    """
    Handles one received radio message.

    Order:
        1. Receive message
        2. Check message format
        3. If valid, send ACK password
        4. Upload pedestrian count
        5. Upload survey counts
    """

    raw_message = raw_message.strip()

    # Ignore empty messages silently
    if not raw_message:
        return

    # Ignore own ACK password echo silently
    if raw_message == ACK_PASSWORD:
        return

    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"\n[{timestamp}] Received message: {raw_message}")

    try:
        node_id, pedestrian_count, a, b, c, d, e = parse_combined_message(raw_message)

    except ValueError:
        # Wrong format, so do nothing and do not send ACK
        return

    print(f"Parsed node_id: {node_id}")
    print(f"Parsed pedestrian_count: {pedestrian_count}")
    print(f"Parsed A: {a}")
    print(f"Parsed B: {b}")
    print(f"Parsed C: {c}")
    print(f"Parsed D: {d}")
    print(f"Parsed E: {e}")

    # Send ACK only after the message format is valid
    send_acknowledgement(serial_connection)

    # Upload pedestrian count
    ped_success, ped_status, ped_response = upload_pedestrian_count(
        node_id,
        pedestrian_count
    )

    if ped_success:
        print(f"Pedestrian upload successful. HTTP status: {ped_status}")
    else:
        print("Pedestrian upload failed.")
        print(f"HTTP status: {ped_status}")
        print(f"Server response/error: {ped_response}")
      
  # Upload survey counts
    survey_success, survey_status, survey_response = upload_survey_counts(
        node_id,
        a,
        b,
        c,
        d,
        e
    )

    if survey_success:
        print(f"Survey upload successful. HTTP status: {survey_status}")
    else:
        print("Survey upload failed.")
        print(f"HTTP status: {survey_status}")
        print(f"Server response/error: {survey_response}")

def main():
    print("Combined pedestrian + survey receiver program started.")
    print(f"Listening on serial port: {SERIAL_PORT}")
    print(f"Baud rate: {BAUD_RATE}")
    print("Press Ctrl+C to stop.\n")

    serial_connection = serial.Serial(
        SERIAL_PORT,
        baudrate=BAUD_RATE,
        timeout=0.1
    )

    buffer = ""
    last_data_time = None

    try:
        while True:
            if serial_connection.in_waiting > 0:
                data = serial_connection.read(serial_connection.in_waiting)

                text = data.decode("utf-8", errors="replace")
                text = text.replace("\r", "\n")

                buffer += text
                last_data_time = time.time()

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    process_message(serial_connection, line)

            # If message arrives without newline, process after 1 second
            if buffer.strip() and last_data_time is not None:
                if time.time() - last_data_time > 1.0:
                    process_message(serial_connection, buffer)
                    buffer = ""
                    last_data_time = None

            time.sleep(0.05)
          
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")

    finally:
        serial_connection.close()
        print("Serial port closed.")
if __name__ == "__main__":
    main()


