from pathlib import Path
import xml.etree.ElementTree as ET


def test_real_go2w_model_has_expected_joint_names() -> None:
    urdf_path = Path(__file__).resolve().parents[1] / "urdf" / "go2w_real.urdf"
    root = ET.fromstring(urdf_path.read_text(encoding="utf-8"))
    joint_names = {
        joint.attrib["name"]
        for joint in root.findall("joint")
        if joint.attrib["name"].endswith("_joint")
    }

    assert {
        "FL_hip_joint",
        "FL_thigh_joint",
        "FL_calf_joint",
        "FL_foot_joint",
    } <= joint_names
    assert {
        "FR_hip_joint",
        "FR_thigh_joint",
        "FR_calf_joint",
        "FR_foot_joint",
    } <= joint_names
    assert {
        "RL_hip_joint",
        "RL_thigh_joint",
        "RL_calf_joint",
        "RL_foot_joint",
    } <= joint_names
    assert {
        "RR_hip_joint",
        "RR_thigh_joint",
        "RR_calf_joint",
        "RR_foot_joint",
    } <= joint_names
    assert "imu_joint" in joint_names
    assert "radar_joint" in joint_names


def test_real_go2w_joint_name_config_uses_urdf_joint_casing() -> None:
    config_path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "joint_names_go2w_description.yaml"
    )
    config_text = config_path.read_text(encoding="utf-8")

    assert "FL_thigh_joint" in config_text
    assert "Fl_thigh_joint" not in config_text
