<?php
/*
------------------------------------------------------------
NodeCheck.php
------------------------------------------------------------

Purpose:
This PHP program monitors the status of a remote node and
the Raspberry Pi receiver.

The Raspberry Pi sends a status update to this PHP file using cURL.

Input format:
    https://checking.com/NodeCheck.php?status=yes
    https://checking.com/NodeCheck.php?status=no

Meaning:
    status=yes  -> The remote node is working
    status=no   -> The remote node is down or has a problem

Important logic:
    Because the Raspberry Pi is the device sending this update,
    every successful update also proves that the Raspberry Pi is
    currently working and connected to the server.

Dashboard URL:
    https://checking.com/NodeCheck.php

Display:
    Node status:
        Green button -> node working
        Red button   -> node down/problem

    Raspberry Pi status:
        Green button -> recent update received from RPI
        Red button   -> no recent update received
------------------------------------------------------------
*/

// Set time zone to Pacific Time
date_default_timezone_set("America/Los_Angeles");

// File used to save latest status on the server
$status_file = "node_check_data.json";

// If no update is received for this long,
// the Raspberry Pi will be shown as down/problem.
$rpi_timeout_seconds = 3 * 60 * 60 + 60 * 15 ; // 3 hours and 15 minutes

// Default data before the first status update
$default_data = [
    "node" => [
        "status" => "no",
        "reported_time" => "No status reported yet"
    ],
    "rpi" => [
        "status" => "no",
        "reported_time" => "No status reported yet"
    ]
];

// Load saved status data
if (file_exists($status_file)) {
    $json_data = file_get_contents($status_file);
    $data = json_decode($json_data, true);

    if (!is_array($data)) {
        $data = $default_data;
    }
} else {
    $data = $default_data;
}

// Make sure both sections exist
if (!isset($data["node"])) {
    $data["node"] = $default_data["node"];
}

if (!isset($data["rpi"])) {
    $data["rpi"] = $default_data["rpi"];
}

// Check whether a new node status was sent
if (isset($_GET["status"])) {
    $new_status = strtolower(trim($_GET["status"]));

    if ($new_status === "yes" || $new_status === "no") {
        $current_time = date("Y-m-d H:i:s");

        // Update node status from the input
        $data["node"]["status"] = $new_status;
        $data["node"]["reported_time"] = $current_time;

        // Since the Raspberry Pi successfully contacted this PHP file,
        // the Raspberry Pi is currently working.
        $data["rpi"]["status"] = "yes";
        $data["rpi"]["reported_time"] = $current_time;

        file_put_contents(
            $status_file,
            json_encode($data, JSON_PRETTY_PRINT)
        );

        header("Content-Type: text/plain");
        echo "Status updated successfully.\n";
        echo "Node status: " . $data["node"]["status"] . "\n";
        echo "Node reported time: " . $data["node"]["reported_time"] . "\n";
        echo "RPI status: " . $data["rpi"]["status"] . "\n";
        echo "RPI reported time: " . $data["rpi"]["reported_time"] . "\n";
        exit;
    } else {
        header("Content-Type: text/plain");
        echo "Invalid status value.\n";
        echo "Use status=yes or status=no.\n";
        exit;
    }
}

// Check if Raspberry Pi status is too old
if ($data["rpi"]["reported_time"] !== "No status reported yet") {
    $last_rpi_time = strtotime($data["rpi"]["reported_time"]);
    $current_server_time = time();

    if (($current_server_time - $last_rpi_time) > $rpi_timeout_seconds) {
        $data["rpi"]["status"] = "no";
    }
}

// Helper function for button color
function button_class($status) {
    if ($status === "yes") {
        return "green-button";
    } else {
        return "red-button";
    }
}

// Helper function for status text
function status_text($status) {
    if ($status === "yes") {
        return "WORKING";
    } else {
        return "DOWN / PROBLEM";
    }
}
?>

<!DOCTYPE html>
<html>
<head>
    <title>Node and Raspberry Pi Status Dashboard</title>

    <meta http-equiv="refresh" content="10">

    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f2f2f2;
            margin: 30px;
        }

        .container {
            max-width: 850px;
            margin: auto;
            background-color: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 0 10px #cccccc;
            text-align: center;
        }

        h1 {
            color: #222222;
        }

        .description {
            text-align: left;
            background-color: #f8f8f8;
            padding: 15px;
            border-left: 5px solid #555555;
            margin-bottom: 25px;
            line-height: 1.5;
        }

        .device-box {
            background-color: #fafafa;
            border: 1px solid #dddddd;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
        }

        .status-button {
            border: none;
            color: white;
            padding: 22px 45px;
            font-size: 22px;
            font-weight: bold;
            border-radius: 12px;
            cursor: default;
            margin: 15px 0;
        }

        .green-button {
            background-color: green;
        }

        .red-button {
            background-color: red;
        }

        .time-box {
            margin-top: 15px;
            font-size: 17px;
            color: #333333;
            padding: 12px;
            background-color: #eeeeee;
            border-radius: 8px;
        }

        .usage {
            text-align: left;
            margin-top: 30px;
            background-color: #fff8dc;
            padding: 15px;
            border-left: 5px solid #e0b000;
            line-height: 1.5;
        }

        code {
            background-color: #eeeeee;
            padding: 3px 6px;
            border-radius: 4px;
        }
    </style>
</head>

<body>
    <div class="container">
        <h1>Node and Raspberry Pi Status Dashboard</h1>

        <div class="description">
            <strong>What this program does:</strong><br>
            This PHP dashboard monitors both the remote node and the Raspberry Pi.
            The Raspberry Pi sends the node status to this PHP page. Because the
            Raspberry Pi is the sender, each successful update also confirms that
            the Raspberry Pi is currently working. If no update is received for too
            long, the Raspberry Pi status automatically changes to down/problem.
        </div>

        <div class="device-box">
            <h2>Remote Node Status</h2>

            <button class="status-button <?php echo button_class($data["node"]["status"]); ?>">
                NODE <?php echo status_text($data["node"]["status"]); ?>
            </button>

            <div class="time-box">
                <strong>Latest node status:</strong>
                <?php echo htmlspecialchars($data["node"]["status"]); ?>
                <br><br>

                <strong>Node status reported time:</strong><br>
                <?php echo htmlspecialchars($data["node"]["reported_time"]); ?>
            </div>
        </div>

        <div class="device-box">
            <h2>Raspberry Pi Status</h2>

            <button class="status-button <?php echo button_class($data["rpi"]["status"]); ?>">
                RPI <?php echo status_text($data["rpi"]["status"]); ?>
            </button>

            <div class="time-box">
                <strong>Latest RPI status:</strong>
                <?php echo htmlspecialchars($data["rpi"]["status"]); ?>
                <br><br>

                <strong>Last update received from RPI:</strong><br>
                <?php echo htmlspecialchars($data["rpi"]["reported_time"]); ?>
            </div>
        </div>

        <div class="usage">
            <strong>How to use this program:</strong><br><br>

            To report that the node is working, run:<br>
            <code>curl "https://checking.com/NodeCheck.php?status=yes"</code>
            <br><br>

            To report that the node is down, run:<br>
            <code>curl "https://checking.com/NodeCheck.php?status=no"</code>
            <br><br>

            To view the dashboard, open:<br>
            <code>https://checking.com/NodeCheck.php</code>
            <br><br>

            Raspberry Pi status is updated automatically whenever the Raspberry Pi
            sends a node status update. If no update is received for more than
            2 hours, the RPI button turns red.
        </div>
    </div>
</body>
</html>
