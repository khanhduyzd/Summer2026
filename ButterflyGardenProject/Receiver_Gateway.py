import serial
import time
import json
import urllib.request
import urllib.error
import stmplib
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

# -----------------------------
# Email settings
# -----------------------------
EMAIL_ALERT_ENABLED = True

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = "email@gmail.com"
SENDER_PASSWORD = "app_password"

RECEIVER_EMAIL = "person_to_warn@example.com"

PEDESTRIAN_API_URL = "https://faridfarahmand.net/CEI/api_pedestrian.php"
SURVEY_API_URL = "https://faridfarahmand.net/CEI/api_survey.php"
STATUS_CHECK_URL = "https://faridfarahmand.net/CEI/NodeCheck.php"

# -----------------------------
# Acknowledgement password
# This is sent back after a valid message is received
# -----------------------------
ACK_PASSWORD = "LED"

# -----------------------------
# Transmitter health monitoring
# -----------------------------
# Transmitter should send one message every hour while awake.
EXPECTED_INTERVAL_SECONDS = 60 * 60

# Missing 3 messages in a row means possible problem.
MAX_MISSED_MESSAGES = 3

# We use 3 hours as the warning timeout:
# 1 expected message/hour + 3 missed messages = about 3 hours.
OFFLINE_TIMEOUT_SECONDS = EXPECTED_INTERVAL_SECONDS * MAX_MISSED_MESSAGES

last_awake_message_time = None
transmitter_awake = False
problem_notified = False
last_node_id = None
        
def update_php_node_status(status):
    """
    Updates the external PHP status dashboard.

    status = "yes" means the node is working.
    status = "no" means the node is down/problem.

    Since the Raspberry Pi sends this request,
    the PHP page also knows the Raspberry Pi is working.
    """

    if status not in ["yes", "no"]:
        print(f"Invalid PHP status value: {status}")
        return False

    url = f"{STATUS_CHECK_URL}?status={status}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            response_body = response.read().decode("utf-8", errors="replace")

        print(f"PHP status update sent: status={status}")
        print(response_body)
        return True

    except Exception as error:
        print(f"PHP status update failed: {error}")
        return False

def parse_combined_message(raw_message):
    """
    Expected message format:
        Gate_01, 09, A, B, C, D, E, mode, battery_code
    """
    raw_message = raw_message.strip()
    raw_message = raw_message.replace("\x00", "")

    # Remove optional Meshtastic prefix.
    if ":" in raw_message:
        raw_message = raw_message.split(":", 1)[1].strip()

    parts = [part.strip() for part in raw_message.split(",")]

    if len(parts) != 9:
        raise ValueError("Message must have 9 fields: node_id, pedestrian_count, a, b, c, d, e, mode, battery_code"  )

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
        mode = int(parts[7])
        battery_code = int(parts[8])
        
    except ValueError:
        raise ValueError("pedestrian_count, survey values, mode, and battery_code must be integers")
        
    if mode not in [0, 1]:
        raise ValueError("mode must be 0 for sleep or 1 for awake")
        
    return node_id, pedestrian_count, a, b, c, d, e, mode, battery_code

def send_acknowledgement(serial_connection):
    #Sends the secret ACK password back to the transmitter.
    serial_connection.write((ACK_PASSWORD + "\n").encode("utf-8"))
    serial_connection.flush()
    
def post_json(api_url, payload):
    #Sends JSON data to one API endpoint.

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
    """ Uploads pedestrian count. JSON format:
            "node_id": "Gate_01",
            "count": 9
    """
    payload = {
        "node_id": node_id,
        "count": pedestrian_count
    }
    return post_json(PEDESTRIAN_API_URL, payload)


def upload_survey_counts(node_id, a, b, c, d, e):
    """ Uploads survey option counts. JSON format:
            "node_id": "Gate_01",
            "a": 1,  "b": 2,   "c": 3,  "d": 4, "e": 5
    """
    payload = {"node_id": node_id,  "a": a,   "b": b, "c": c, "d": d,  "e": e }
    return post_json(SURVEY_API_URL, payload)
        
def send_warning_email(subject, body):
    """
    Sends a warning email when a transmitter problem is detected.
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
            
def notify_transmitter_problem(node_id):
    """
    Runs when the transmitter/node may have a problem.

    This function:
    1. Updates the PHP dashboard with status=no
    2. Sends a warning email
    """

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = f"LoRa transmitter warning: {node_id}"

    body = f"""
Warning: Possible transmitter problem detected.

Node ID: {node_id}
Receiver ID: RPI_01
Time: {timestamp}

Reason:
The transmitter was expected to be awake, but the Raspberry Pi has not received a valid message for too long.

Recommended action:
Please check the transmitter node, battery, antenna, LoRa connection, and Raspberry Pi receiver.
"""
    # Node is down/problem.
    # Since the RPI sends this request, PHP knows the RPI is still working.
    update_php_node_status("no")

    # Send email warning.
    send_warning_email(subject, body)

def check_transmitter_health():
    """
    Checks if the transmitter has missed too many expected messages.
    If transmitter is sleeping, this function does nothing.
    If transmitter is awake and no message is received for too long,
    it prints a warning.
    """

    global last_awake_message_time
    global transmitter_awake
    global problem_notified
    global last_node_id

    if not transmitter_awake:
        return

    if last_awake_message_time is None:
        return

    elapsed_time = time.time() - last_awake_message_time

    if elapsed_time > OFFLINE_TIMEOUT_SECONDS and not problem_notified:
        notify_transmitter_problem(last_node_id)
        problem_notified = True

def process_message(serial_connection, raw_message):
    """ Handles one received radio message.
    Order:
        1. Receive message
        2. Check message format
        3. If valid, send the ACK password
        4. Update transmitter awake/sleep status
        5. Upload pedestrian count
        6. Upload survey counts.
    """
    
    global last_awake_message_time
    global transmitter_awake
    global problem_notified
    global last_node_id
    raw_message = raw_message.strip()

    # Ignore empty messages
    if not raw_message:
        return

    timestamp = datetime.now().isoformat(timespec="seconds")
    print(f"\n[{timestamp}] Received message: {raw_message}")

    try:
        node_id, pedestrian_count, a, b, c, d, e, mode, battery_code = parse_combined_message(raw_message)
        battery_voltage = (1.024*4095)/battery_code
    except ValueError:
        # Wrong format, so do nothing and do not send ACK
        return

    # Send ACK only after the message format is valid
    send_acknowledgement(serial_connection)
    
    # Update transmitter awake/sleep status
    last_node_id = node_id
    if mode == 1:
        transmitter_awake = True
        last_awake_message_time = time.time()
        problem_notified = False
        print("Transmitter status: AWAKE")

    elif mode == 0:
        transmitter_awake = False
        last_awake_message_time = None
        problem_notified = False
        print("Transmitter status: SLEEP")
    
    # Upload pedestrian count
    ped_success, ped_status, ped_response = upload_pedestrian_count(
        node_id,
        pedestrian_count
    )

    if ped_success:
        print(f"Pedestrian upload successful.")
    else:
        print("Pedestrian upload failed.")
        print(f"HTTP status: {ped_status}")
        print(f"Server response/error: {ped_response}")
      
  # Upload survey counts
    survey_success, survey_status, survey_response = upload_survey_counts(node_id, a, b, c, d, e )

    if survey_success:
        print(f"Survey upload successful.")
    else:
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

            # If message arrives without newline, process after 1 second
            if buffer.strip() and last_data_time is not None:
                if time.time() - last_data_time > 1.0:
                    process_message(serial_connection, buffer)
                    buffer = ""
                    last_data_time = None
                    
            # Check whether awake transmitter has missed too many messages
            check_transmitter_health()
            
            time.sleep(0.05)
          
    except KeyboardInterrupt:
        print("Program stopped by user.")

    finally:
        serial_connection.close()
        print("Serial port closed.")
if __name__ == "__main__":
    main()


