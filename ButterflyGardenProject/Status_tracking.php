<?php
// File used to save the latest status data on the server
$status_file = "status_data.json";

// If the Raspberry Pi does not update for this long,
// the page will automatically show RPI as offline/problem.
$rpi_timeout_seconds = 10 * 60; // 10 minutes

// Default status before any update is received
$default_data = [
    "rpi" => [
        "status" => "no",
        "time" => "No update yet"
    ],
    "transmitter" => [
        "status" => "no",
        "time" => "No update yet"
    ]
];

// --------------------------------------
// Load existing saved data
// --------------------------------------
if (file_exists($status_file)) {
    $json = file_get_contents($status_file);
    $data = json_decode($json, true);

    if (!is_array($data)) {
        $data = $default_data;
    }
} else {
    $data = $default_data;
}

// Make sure both sections exist
if (!isset($data["rpi"])) {
    $data["rpi"] = $default_data["rpi"];
}

if (!isset($data["transmitter"])) {
    $data["transmitter"] = $default_data["transmitter"];
}

// --------------------------------------
// Read input parameters
// --------------------------------------
$device = isset($_GET["device"]) ? strtolower($_GET["device"]) : "";
$status = isset($_GET["status"]) ? strtolower($_GET["status"]) : "";

// --------------------------------------
// Update status if valid parameters are provided
// --------------------------------------
if (
    ($device == "rpi" || $device == "transmitter") &&
    ($status == "yes" || $status == "no")
) {
    $data[$device]["status"] = $status;
    $data[$device]["time"] = date("Y-m-d H:i:s");

    file_put_contents($status_file, json_encode($data, JSON_PRETTY_PRINT));
}

// --------------------------------------
// Automatic RPI timeout check
// If the RPI has not sent heartbeat recently,
// --------------------------------------
if ($data["rpi"]["time"] != "No update yet") {
    $last_rpi_time = strtotime($data["rpi"]["time"]);
    $current_time = time();

    if (($current_time - $last_rpi_time) > $rpi_timeout_seconds) {
        $data["rpi"]["status"] = "no";
    }
}

// --------------------------------------
// Helper functions
// --------------------------------------
function led_color($status) {
    if ($status == "yes") {
        return "green";
    } else {
        return "red";
    }
}

function status_text($status) {
    if ($status == "yes") {
        return "ONLINE / OK";
    } else {
        return "OFFLINE / PROBLEM";
    }
}
?>

<!DOCTYPE html>
<html>
<head>
    <title>RPI and Transmitter Status</title>

    <!-- Refresh page every 10 seconds -->
    <meta http-equiv="refresh" content="10">

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f2f2f2;
            margin: 30px;
        }

        h1 {
            text-align: center;
            color: #222222;
        }

        .container {
            max-width: 800px;
            margin: auto;
        }

        .box {
            background: white;
            padding: 25px;
            margin: 20px 0;
            border-radius: 10px;
            box-shadow: 0 0 8px #cccccc;
        }

        h2 {
            margin-top: 0;
            color: #333333;
        }

        .status-row {
            display: flex;
            align-items: center;
            gap: 15px;
            font-size: 22px;
            font-weight: bold;
        }

        .led {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #555555;
        }

        .green {
            background: green;
        }

        .red {
            background: red;
        }

        .time {
            margin-top: 15px;
            font-size: 16px;
            color: #555555;
        }

        .note {
            max-width: 800px;
            margin: 20px auto;
            padding: 15px;
            background: #fff8dc;
            border-left: 5px solid #e0b000;
            font-size: 15px;
        }
    </style>
</head>

<body>
    <div class="container">
        <h1>RPI and Transmitter Status Dashboard</h1>

        <div class="box">
            <h2>Raspberry Pi Status</h2>

            <div class="status-row">
                <span class="led <?php echo led_color($data["rpi"]["status"]); ?>"></span>
                <span><?php echo status_text($data["rpi"]["status"]); ?></span>
            </div>

            <div class="time">
                Last RPI update:
                <?php echo htmlspecialchars($data["rpi"]["time"]); ?>
            </div>
        </div>

        <div class="box">
            <h2>Transmitter Status</h2>

            <div class="status-row">
                <span class="led <?php echo led_color($data["transmitter"]["status"]); ?>"></span>
                <span><?php echo status_text($data["transmitter"]["status"]); ?></span>
            </div>

            <div class="time">
                Last transmitter update:
                <?php echo htmlspecialchars($data["transmitter"]["time"]); ?>
            </div>
        </div>
    </div>

    <div class="note">
        RPI status is based on heartbeat updates. If the Raspberry Pi does not send an update for more than 10 minutes, the RPI LED will automatically turn red.
    </div>
</body>
</html>
