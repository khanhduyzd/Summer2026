<?php
/*
------------------------------------------------------------
Node Status Monitoring Dashboard
------------------------------------------------------------

Purpose:
This PHP program monitors the status of a remote node.

The node can report its condition by sending a URL request
to this PHP file.

Input format:
    https://checking.com/api_status.php?status=yes
    https://checking.com/api_status.php?status=no

Meaning:
    status=yes  -> The node is working
    status=no   -> The node is down or has a problem

The program saves the latest reported status and the time
that status was received. When a user opens the page, the
node status is displayed using a colored button:

    Green button -> Node is working
    Red button   -> Node is down

This PHP file should be placed on a web server that supports PHP.
------------------------------------------------------------
*/

// File used to save the latest node status
$status_file = "node_status_data.json";

// Default data before the first report is received
$default_data = [
    "status" => "no",
    "reported_time" => "No status reported yet"
];

// Load previous status data if it exists
if (file_exists($status_file)) {
    $json_data = file_get_contents($status_file);
    $data = json_decode($json_data, true);

    if (!is_array($data)) {
        $data = $default_data;
    }
} else {
    $data = $default_data;
}

// Read input parameter from URL
// Example: api_status.php?status=yes
if (isset($_GET["status"])) {
    $new_status = strtolower(trim($_GET["status"]));

    // Only accept yes or no
    if ($new_status === "yes" || $new_status === "no") {
        $data["status"] = $new_status;
        $data["reported_time"] = date("Y-m-d H:i:s");

        // Save latest status to file
        file_put_contents($status_file, json_encode($data, JSON_PRETTY_PRINT));
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

    <!-- Refresh page every 10 seconds -->
    <meta http-equiv="refresh" content="10">

    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f2f2f2;
            margin: 30px;
        }

        .container {
            max-width: 700px;
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
            <strong>Purpose:</strong><br>
            This dashboard monitors the state of a remote node. The node reports
            whether it is working or down by sending a status value to this PHP page.
            The latest status and report time are saved on the server.
        </div>

        <button class="status-button <?php echo $button_class; ?>">
            <?php echo $status_text; ?>
        </button>

        <div class="time-box">
            <strong>Status reported time:</strong><br>
            <?php echo htmlspecialchars($data["reported_time"]); ?>
        </div>

        <div class="usage">
            <strong>How to use this program:</strong><br><br>

            To report that the node is working, open or call:<br>
            <code>https://checking.com/api_status.php?status=yes</code>
            <br><br>

            To report that the node is down, open or call:<br>
            <code>https://checking.com/api_status.php?status=no</code>
            <br><br>

            To view the dashboard only, open:<br>
            <code>https://checking.com/api_status.php</code>
        </div>
    </div>
</body>
</html>
