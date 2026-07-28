import serial
import time
import json
import urllib.request
import urllib.error
import smtplib
from email.message import EmailMessage
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
STATUS_CHECK_URL = "https://faridfarahmand.net/CEI/NodeCheck.php"

# -----------------------------
# Email settings
# -----------------------------
EMAIL_ALERT_ENABLED = True

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = "email@gmail.com"
SENDER_PASSWORD = "app_password"

RECEIVER_EMAIL = "person_to_warn@example.com"

# -----------------------------
# Acknowledgement password
# -----------------------------
ACK_PASSWORD = "LED"

# -----------------------------
# New node status logic
# -----------------------------
# Final version: 1 hour
NODE_TIMEOUT_SECONDS = 60 * 60

# If node is still down, send status=no again every 1 hour
STATUS_UPDATE_INTERVAL_SECONDS = 60 * 60

# For testing only, you can temporarily use:
# NODE_TIMEOUT_SECONDS = 60
# STATUS_UPDATE_INTERVAL_SECONDS = 60

last_valid_message_time = time.time()
last_status_update_time = 0
node_is_down = False
problem_notified = False
last_node_id = "Gate_01"


def update_php_node_status(status):
    """
    Sends node status to PHP.

    status=yes:
        Node sent a correct awake message.
        RPI is also working because RPI sent this request.

    status=no:
        Node sent a wrong message, sleep message, or no valid message arrived in time.
        RPI is also working because RPI sent this request.
    """

    if status not in ["yes", "no"]:
        print(f"Invalid PHP status value: {status}")
        return False

    url = f"{STATUS_CHECK_URL}?status={status}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            response.read()

        print(f"PHP status sent: {status}")
        return True

    except Exception as error:
        print(f"PHP status update failed: {error}")
        return False


def parse_combined_message(raw_message):
    """
    Expected message format:
        Gate_01, pedestrian_count, A, B, C, D, E, mode, battery_code

    Example:
        Gate_01,0,0,0,0,0,0,1,1000

    mode:
        1 = awake
        0 = sleep
    """

    raw_message = raw_message.strip()
    raw_message = raw_message.replace("\x00", "")
    raw_message = "".join(ch for ch in raw_message if ch.isprintable())

    # Remove optional Meshtastic prefix.
    # Example:
    # 8798: Gate_01,0,0,0,0,0,0,1,1000
    if ":" in raw_message:
        raw_message = raw_message.split(":", 1)[1].strip()

    # Find the real start of the message.
    # This helps if extra characters appear before Gate_01.
    gate_index = raw_message.lower().find("gate_01")

    if gate_index == -1:
        raise ValueError("Gate_01 not found in message")

    raw_message = raw_message[gate_index:]

    parts = [part.strip() for part in raw_message.split(",")]

    # Keep only the first 9 fields if extra text appears after the message.
    if len(parts) > 9:
        parts = parts[:9]

    if len(parts) != 9:
        raise ValueError(
            "Message must have 9 fields: node_id, pedestrian_count, a, b, c, d, e, mode, battery_code"
        )

    node_id = parts[0]

    if not node_id:
        raise ValueError("node_id is empty")

    if node_id.lower() != "gate_01":
        raise ValueError(f"Unexpected node_id: {node_id}")

    try:
        pedestrian_count = int(parts[1])
        a = int(parts[2])
        b = int(parts[3])
        c = int(parts[4])
        d = int(parts[5])
        e = int(parts[6])
        mode = int(parts[7])
        battery_code = int(parts[8])

    except ValueError:
        raise ValueError(
            "pedestrian_count, survey values, mode, and battery_code must be integers"
        )

    if mode not in [0, 1]:
        raise ValueError("mode must be 0 for sleep or 1 for awake")

    if battery_code <= 0:
        raise ValueError("battery_code must be greater than 0")

    return node_id, pedestrian_count, a, b, c, d, e, mode, battery_code


def send_acknowledgement(serial_connection):
    """
    Sends the secret ACK password back to the transmitter.
    """

    serial_connection.write((ACK_PASSWORD + "\n").encode("utf-8"))
    serial_connection.flush()


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

            return False, status_code, response_body

    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        return False, error.code, response_body

    except urllib.error.URLError as error:
        return False, None, str(error)


def upload_pedestrian_count(node_id, pedestrian_count):
    """
    Uploads pedestrian count.
    """

    payload = {
        "node_id": node_id,
        "count": pedestrian_count
    }

    return post_json(PEDESTRIAN_API_URL, payload)


def upload_survey_counts(node_id, a, b, c, d, e):
    """
    Uploads survey option counts.
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


def send_warning_email(subject, body):
    """
    Sends a warning email when no valid message is received in time.
    """

    if not EMAIL_ALERT_ENABLED:
        return False

    message = EmailMessage()
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)

        return True

    except Exception as error:
        print(f"Warning email failed: {error}")
        return False


def send_timeout_warning_email(node_id):
    """
    Sends one warning email when no valid message arrives in time.
    """

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = f"LoRa transmitter warning: {node_id}"

    body = f"""
Warning: Possible transmitter problem detected.

Node ID: {node_id}
Receiver ID: RPI_01
Time: {timestamp}

Reason:
The Raspberry Pi has not received a valid message from the transmitter within the expected time.

Recommended action:
Please check the transmitter node, battery, antenna, LoRa connection, and Raspberry Pi receiver.
"""

    send_warning_email(subject, body)


def check_node_timeout_and_update_php():
    """
    New logic:

    If no valid message has been received within NODE_TIMEOUT_SECONDS,
    send status=no to PHP.

    If the node is still down, send status=no again every
    STATUS_UPDATE_INTERVAL_SECONDS.
    """

    global node_is_down
    global last_status_update_time
    global problem_notified

    current_time = time.time()
    time_since_valid_message = current_time - last_valid_message_time
    time_since_last_status_update = current_time - last_status_update_time

    if time_since_valid_message >= NODE_TIMEOUT_SECONDS:

        if not node_is_down:
            update_php_node_status("no")
            print("No valid message received in time. PHP status=no sent.")

            last_status_update_time = current_time
            node_is_down = True

            if not problem_notified:
                send_timeout_warning_email(last_node_id)
                problem_notified = True

        elif time_since_last_status_update >= STATUS_UPDATE_INTERVAL_SECONDS:
            update_php_node_status("no")
            print("Node still down. Repeated PHP status=no sent.")

            last_status_update_time = current_time


def process_message(serial_connection, raw_message):
    """
    Handles one received radio message.

    Correct awake message, mode = 1:
        - Send ACK
        - Send status=yes to PHP
        - Upload to database

    Sleep message, mode = 0:
        - Send ACK
        - Send status=no to PHP
        - Do not upload to database

    Wrong/invalid message:
        - Send status=no to PHP
        - Do not send ACK
        - Do not upload to database
    """

    global last_valid_message_time
    global last_status_update_time
    global node_is_down
    global problem_notified
    global last_node_id

    raw_message = raw_message.strip()

    if not raw_message:
        return

    try:
        node_id, pedestrian_count, a, b, c, d, e, mode, battery_code = parse_combined_message(raw_message)

        # battery_code is checked for validity, but not used right now.
        _ = battery_code

    except ValueError as error:
        print(f"Invalid message ignored: {error}")
        print(f"Bad message was: {repr(raw_message)}")

        update_php_node_status("no")
        print("PHP status=no sent because message was invalid.")

        last_status_update_time = time.time()
        node_is_down = True

        return

    # Message format is valid, so send ACK.
    send_acknowledgement(serial_connection)

    current_time = time.time()
    last_valid_message_time = current_time
    last_status_update_time = current_time
    last_node_id = node_id

    # mode = 0 means the node says it is sleeping.
    # For your current dashboard logic, sleep is shown as no.
    if mode == 0:
        node_is_down = True
        update_php_node_status("no")
        print("Node reported sleep mode. PHP status=no sent.")

        # Do not upload sleep message to database.
        return

    # mode = 1 means node is awake and working.
    node_is_down = False
    problem_notified = False

    update_php_node_status("yes")
    print("Valid awake message received. PHP status=yes sent.")

    # Upload pedestrian count.
    ped_success, ped_status, ped_response = upload_pedestrian_count(
        node_id,
        pedestrian_count
    )

    if not ped_success:
        print("Pedestrian upload failed.")
        print(f"HTTP status: {ped_status}")
        print(f"Server response/error: {ped_response}")

    # Upload survey counts.
    survey_success, survey_status, survey_response = upload_survey_counts(
        node_id,
        a,
        b,
        c,
        d,
        e
    )

    if not survey_success:
        print("Survey upload failed.")
        print(f"HTTP status: {survey_status}")
        print(f"Server response/error: {survey_response}")


def main():
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

            # If message arrives without newline, process after 3 seconds.
            if buffer.strip() and last_data_time is not None:
                if time.time() - last_data_time > 3.0:
                    process_message(serial_connection, buffer)
                    buffer = ""
                    last_data_time = None

            # New logic:
            # If no valid message arrives in time, send status=no.
            check_node_timeout_and_update_php()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("Program stopped by user.")

    finally:
        serial_connection.close()
        print("Serial port closed.")


if __name__ == "__main__":
    main()
