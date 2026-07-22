<?php
date_default_timezone_set("America/Los_Angeles");

$status_file = "node_check_data.json";
$rpi_timeout_seconds = 75 * 60; // 1 hour and 15 minutes

$default_data = [
    "node" => [
        "status" => "no",
        "current_status_time" => "No status reported yet",
        "last_working_time" => "No working time yet",
        "last_down_time" => "No down time yet"
    ],
    "rpi" => [
        "status" => "no",
        "current_status_time" => "No status reported yet",
        "last_working_time" => "No working time yet",
        "last_down_time" => "No down time yet"
    ]
];

if (file_exists($status_file)) {
    $json_data = file_get_contents($status_file);
    $data = json_decode($json_data, true);

    if (!is_array($data)) {
        $data = $default_data;
    }
} else {
    $data = $default_data;
}

foreach ($default_data as $device => $device_data) {
    if (!isset($data[$device])) {
        $data[$device] = $device_data;
    }

    foreach ($device_data as $key => $value) {
        if (!isset($data[$device][$key])) {
            $data[$device][$key] = $value;
        }
    }
}

function save_data($status_file, $data) {
    file_put_contents($status_file, json_encode($data, JSON_PRETTY_PRINT));
}

function format_duration($seconds) {
    if ($seconds < 0) {
        $seconds = 0;
    }

    $days = floor($seconds / 86400);
    $seconds %= 86400;

    $hours = floor($seconds / 3600);
    $seconds %= 3600;

    $minutes = floor($seconds / 60);

    if ($days > 0) {
        return $days . " day(s), " . $hours . " hour(s), " . $minutes . " minute(s)";
    }

    if ($hours > 0) {
        return $hours . " hour(s), " . $minutes . " minute(s)";
    }

    return $minutes . " minute(s)";
}

function down_for_text($device_data) {
    if ($device_data["status"] === "yes") {
        return "Not down";
    }

    if ($device_data["last_down_time"] !== "No down time yet") {
        $down_timestamp = strtotime($device_data["last_down_time"]);

        if ($down_timestamp !== false) {
            return format_duration(time() - $down_timestamp);
        }
    }

    return "Unknown";
}

function status_text($status) {
    if ($status === "yes") {
        return "WORKING";
    }

    return "DOWN / PROBLEM";
}

function button_class($status) {
    if ($status === "yes") {
        return "green-button";
    }

    return "red-button";
}

if (isset($_GET["status"])) {
    $new_status = strtolower(trim($_GET["status"]));

    if ($new_status === "yes" || $new_status === "no") {
        $current_time = date("Y-m-d H:i:s");

        if ($new_status === "yes") {
            $data["node"]["status"] = "yes";
            $data["node"]["current_status_time"] = $current_time;
            $data["node"]["last_working_time"] = $current_time;
        }

        if ($new_status === "no") {
            if ($data["node"]["status"] !== "no") {
                $data["node"]["last_down_time"] = $current_time;
            }

            $data["node"]["status"] = "no";
            $data["node"]["current_status_time"] = $current_time;
        }

        $data["rpi"]["status"] = "yes";
        $data["rpi"]["current_status_time"] = $current_time;
        $data["rpi"]["last_working_time"] = $current_time;

        save_data($status_file, $data);

        header("Content-Type: text/plain");
        echo "Status updated successfully.\n";
        echo "Node status: " . $data["node"]["status"] . "\n";
        echo "RPI status: " . $data["rpi"]["status"] . "\n";
        exit;
    } else {
        header("Content-Type: text/plain");
        echo "Invalid status value.\n";
        echo "Use status=yes or status=no.\n";
        exit;
    }
}

if ($data["rpi"]["current_status_time"] !== "No status reported yet") {
    $last_rpi_update = strtotime($data["rpi"]["current_status_time"]);

    if ($last_rpi_update !== false) {
        $elapsed = time() - $last_rpi_update;

        if ($elapsed > $rpi_timeout_seconds) {
            if ($data["rpi"]["status"] !== "no") {
                $data["rpi"]["last_down_time"] = date("Y-m-d H:i:s");
            }

            $data["rpi"]["status"] = "no";
        }
    }
}

save_data($status_file, $data);

$node_down_for = down_for_text($data["node"]);
$rpi_down_for = down_for_text($data["rpi"]);
?>

<!DOCTYPE html>
<html>
<head>
    <title>Status Dashboard</title>
    <meta http-equiv="refresh" content="10">

    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f2f2f2;
            margin: 25px;
        }

        .container {
            max-width: 1300px;
            margin: auto;
            background-color: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 0 10px #cccccc;
            text-align: center;
        }

        h1 {
            color: #222222;
            margin-bottom: 25px;
        }

        .dashboard-row {
            display: flex;
            gap: 20px;
            align-items: stretch;
            justify-content: center;
        }

        .card {
            flex: 1;
            background-color: #fafafa;
            border: 1px solid #dddddd;
            border-radius: 10px;
            padding: 22px;
            text-align: center;
        }

        .status-button {
            border: none;
            color: white;
            padding: 20px 35px;
            font-size: 21px;
            font-weight: bold;
            border-radius: 12px;
            cursor: default;
            margin: 15px 0;
            width: 90%;
        }

        .green-button {
            background-color: green;
        }

        .red-button {
            background-color: red;
        }

        .info-box {
            font-size: 16px;
            color: #333333;
            padding: 15px;
            background-color: #eeeeee;
            border-radius: 8px;
            text-align: left;
            line-height: 1.6;
            margin-top: 15px;
        }

        .label {
            font-weight: bold;
        }

        @media (max-width: 900px) {
            .dashboard-row {
                flex-direction: column;
            }
        }
    </style>
</head>

<body>
    <div class="container">
        <h1>Status Dashboard</h1>

        <div class="dashboard-row">

            <div class="card">
                <h2>Transmitter Remote Node</h2>

                <button class="status-button <?php echo button_class($data["node"]["status"]); ?>">
                    NODE <?php echo status_text($data["node"]["status"]); ?>
                </button>

                <div class="info-box">
                    <span class="label">Current status:</span><br>
                    <?php echo htmlspecialchars(status_text($data["node"]["status"])); ?>
                    <br><br>

                    <span class="label">Current status time:</span><br>
                    <?php echo htmlspecialchars($data["node"]["current_status_time"]); ?>
                    <br><br>

                    <span class="label">Last working time:</span><br>
                    <?php echo htmlspecialchars($data["node"]["last_working_time"]); ?>
                    <br><br>

                    <span class="label">Down for:</span><br>
                    <?php echo htmlspecialchars($node_down_for); ?>
                </div>
            </div>

            <div class="card">
                <h2>Raspberry Pi</h2>

                <button class="status-button <?php echo button_class($data["rpi"]["status"]); ?>">
                    RPI <?php echo status_text($data["rpi"]["status"]); ?>
                </button>

                <div class="info-box">
                    <span class="label">Current status:</span><br>
                    <?php echo htmlspecialchars(status_text($data["rpi"]["status"])); ?>
                    <br><br>

                    <span class="label">Last update received:</span><br>
                    <?php echo htmlspecialchars($data["rpi"]["current_status_time"]); ?>
                    <br><br>

                    <span class="label">Last working time:</span><br>
                    <?php echo htmlspecialchars($data["rpi"]["last_working_time"]); ?>
                    <br><br>

                    <span class="label">Down for:</span><br>
                    <?php echo htmlspecialchars($rpi_down_for); ?>
                </div>
            </div>

        </div>
    </div>
</body>
</html>
