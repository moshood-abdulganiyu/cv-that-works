"""Calibration ladder: 8 fictional CVs. Each rung keeps the flaws of the rung above and adds more.
Everything here is made up. These CVs are for testing the checker only, never for training a model."""
import re
from pathlib import Path

S = Path(__file__).parent / "samples"
BASE = (S / "strong_fictional.txt").read_text(encoding="utf-8")


def swap(t, pairs):
    for a, b in pairs:
        assert a in t, a
        t = t.replace(a, b)
    return t


def drop_section(t, heading):
    return re.sub(rf"(?m)^{re.escape(heading)}\n(?:(?!^(?:Summary|Education|Projects|Leadership and Volunteering|Experience|Skills|Awards|Certifications and Training|Languages)$).*\n?)*", "", t)


def rungs():
    r = {}
    r["R8 strong"] = BASE
    t = swap(BASE, [("sample.studenttwo@gmail.com", "sweetgirl2002@yahoo.com"), (" | linkedin.com/in/sample-studenttwo", "")])
    r["R7 casual email, no LinkedIn"] = t
    t = swap(t, [("Built a web tool that logged 240 maintenance reports across 3 departments in 5 months", "Built a web tool that logged maintenance reports across departments"),
                 ("Reduced average response time from 9 days to 4 days by routing reports to the right officer", "Reduced response time by routing reports to the right officer"),
                 ("Presented the tool to 25 staff members, resulting in adoption by the Estates office", "Presented the tool to staff, resulting in adoption by the Estates office")])
    r["R6 fewer numbers"] = t
    t = swap(t, [(re.search(r"(?m)^Final-year.*$", t).group(0), "Passionate and hardworking student with a proven track record. A team player seeking opportunities.")])
    r["R5 cliché summary"] = t
    t = swap(t, [("Lead a team of 6 officers running weekly sessions for 40 members", "Responsible for running weekly sessions for the club"),
                 ("Taught basic computer skills to 30 secondary school students over 8 Saturdays", "Helped with teaching computer skills to students"),
                 ("Documented 12 support procedures used by a team of 4", "Worked on support procedures for the team")])
    t = re.sub(r"(?m)^Awards\n.*\n", "", t)
    t = re.sub(r"(?m)^Certifications and Training\n.*\n", "", t)
    t = re.sub(r"(?m)^Languages\n.*\n?", "", t)
    r["R4 weak phrases, thin extras"] = t
    lines = []
    for l in t.splitlines():
        lines.append(re.sub(r"\s?\b\d[\d,]*\b", "", l) if l.startswith("- ") and "CGPA" not in l else l)
    t = "\n".join(lines) + "\n"
    r["R3 no numbers"] = t
    t = drop_section(t, "Projects")
    t = drop_section(t, "Leadership and Volunteering")
    t = t.replace(" | +234 803 123 4567", "")
    r["R2 no projects, leadership or phone"] = t
    r["R1 weak fictional"] = (S / "weak_fictional.txt").read_text(encoding="utf-8")
    return r
