<?php
/*
------------------------------------------------------------
NodeCheck.php
------------------------------------------------------------

Purpose:
This PHP program monitors the latest reported status of a
remote node.

A remote device, Raspberry Pi, or user can send a status update
to this program using cURL.

Input format:
    https://checking.com/NodeCheck.php?status=yes
    https://checking.com/NodeCheck.php?status=no

Meaning:
    status=yes  -> The node is working
    status=no   -> The node is down or has a problem

Behavior:
1. When a status parameter is received, the program saves the
   latest status and the report time into a JSON file.
2. When a user visits the main PHP page without a status
   parameter, the page displays the latest saved node state.
3. The node state is shown as a button:
      Green -> yes / node working
      Red   -> no / node down

Example cURL commands:
    curl "https://checking.com/NodeCheck.php?status=yes"
    curl "https://checking.com/NodeCheck.php?status=no"

Dashboard URL:
    https://checking.com/NodeCheck.php
------------------------------------------------------------
*/
// Set time zone to UTC-7 / Pacific Time
date_default_timezone_set("America/Los_Angeles");

// File used to save latest node status on the server
$status_file = "node_status_data.json";

// Default data before the first status update
$default_data = [
    "status" => "no",
    "reported_time" => "No status reported yet"
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

// Check whether a new status was sent
if (isset($_GET["status"])) {
    $new_status = strtolower(trim($_GET["status"]));

    if ($new_status === "yes" || $new_status === "no") {
        $data["status"] = $new_status;
        $data["reported_time"] = date("Y-m-d H:i:s");

        file_put_contents(
            $status_file,
            json_encode($data, JSON_PRETTY_PRINT)
        );

        // Simple response for cURL users
        if (php_sapi_name() !== "cli") {
            header("Content-Type: text/plain");
            echo "Status updated successfully.\n";
            echo "Node status: " . $data["status"] . "\n";
            echo "Reported time: " . $data["reported_time"] . "\n";
            exit;
        }
    } else {
        header("Content-Type: text/plain");
        echo "Invalid status value.\n";
        echo "Use status=yes or status=no.\n";
        exit;
    }
}

// Decide button color and display text
if ($data["status"] === "yes") {
    $button_class = "green-button";
    $status_text = "NODE WORKING";
} else {
    $button_class = "red-button";
    $status_text = "NODE DOWN";
}
?>

<!DOCTYPE html>
<html>
<head>
    <title>Node Status Dashboard</title>

    <meta http-equiv="refresh" content="10">

    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f2f2f2;
            margin: 30px;
        }

        .container {
            max-width: 750px;
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

        .status-button {
            border: none;
            color: white;
            padding: 25px 50px;
            font-size: 24px;
            font-weight: bold;
            border-radius: 12px;
            cursor: default;
            margin: 20px 0;
        }

        .green-button {
            background-color: green;
        }

        .red-button {
            background-color: red;
        }

        .time-box {
            margin-top: 20px;
            font-size: 18px;
            color: #333333;
            padding: 15px;
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
        <h1>Node Status Dashboard</h1>

        <div class="description">
            <strong>What this node does:</strong><br>
            This dashboard monitors the latest reported state of a remote node.
            The node can be a transmitter, sensor, Raspberry Pi, or any remote
            device that needs to report whether it is working or down.
            The latest status is saved on the server and displayed here.
        </div>

        <button class="status-button <?php echo $button_class; ?>">
            <?php echo $status_text; ?>
        </button>

        <div class="time-box">
            <strong>Latest reported status:</strong>
            <?php echo htmlspecialchars($data["status"]); ?>
            <br><br>

            <strong>Status reported time:</strong><br>
            <?php echo htmlspecialchars($data["reported_time"]); ?>
        </div>

        <div class="usage">
            <strong>How to use this program:</strong><br><br>

            To update the node as working, run:<br>
            <code>curl "https://checking.com/NodeCheck.php?status=yes"</code>
            <br><br>

            To update the node as down, run:<br>
            <code>curl "https://checking.com/NodeCheck.php?status=no"</code>
            <br><br>

            To view the latest node status, open:<br>
            <code>https://checking.com/NodeCheck.php</code>
        </div>
    </div>
</body>
</html>
