"""Rubric constants. One place to change weights, bands and word lists.
Rubric version is stamped on every report. Change the version when any number here changes."""

RUBRIC_VERSION = "cv-rubric-v1.2"

MAX_POINTS = {
    "evidence": 20, "bullets": 20, "sections": 15, "summary": 10,
    "contact": 10, "language": 10, "format": 10, "fit": 5,
}
LABELS = {
    "evidence": "Evidence and numbers", "bullets": "Bullet quality", "sections": "Sections present",
    "summary": "Opening summary", "contact": "Contact and first impression",
    "language": "Language and voice", "format": "Format and length", "fit": "Fit to goal",
}
BANDS = [(85, "Ready"), (70, "Nearly"), (50, "Needs work"), (0, "Rebuild")]
TARGETS = ["internship", "scholarship", "graduate study", "leadership", "not sure"]

# Default upload limit. Vercel functions accept about 4.5 MB bodies, so stay under that. Final value is set in step 4.
MAX_FILE_BYTES = 4 * 1024 * 1024

# Sections: key -> accepted headings (lower case, "&" written as "and")
SECTION_ALIASES = {
    "summary": ["summary", "profile", "objective", "personal statement", "about me", "career objective", "professional summary", "personal profile"],
    "education": ["education", "academic background", "academic qualifications", "education and qualifications", "educational background"],
    "projects": ["projects", "academic projects", "research projects", "selected projects", "project experience", "personal projects"],
    "experience": ["experience", "work experience", "professional experience", "internships", "internship experience", "employment history", "relevant experience"],
    "leadership": ["leadership", "volunteering", "leadership and volunteering", "volunteer experience", "volunteer work", "leadership experience",
                   "community service", "extracurricular activities", "activities", "community engagement", "leadership and community service"],
    "skills": ["skills", "technical skills", "key skills", "core skills", "skills and interests", "skills and languages", "skills and tools"],
    "awards": ["awards", "honours", "honors", "awards and achievements", "achievements", "scholarships and awards", "awards and honours"],
    "memberships": ["memberships", "professional memberships", "associations", "professional associations", "memberships and associations", "affiliations"],
    "certifications": ["certifications", "certificates", "certifications and training", "training", "courses", "training and certifications", "licenses and certifications"],
    "languages": ["languages", "language skills"],
}
# Course-specific names for placements and practical training. All count as Experience.
SECTION_ALIASES["experience"] += ["siwes", "siwes experience", "industrial attachment", "industrial training experience", "field attachment", "farm practical year",
    "farm practical", "practicum", "clinical postings", "clinical posting", "clinical rotations", "clinical rotation", "clinical experience",
    "clinical placements", "clinical placement", "housemanship", "housemanship rotations", "laboratory experience", "teaching practice", "practical training",
    "internship and practical experience", "placements"]

ALIAS_TO_SECTION = {a: k for k, v in SECTION_ALIASES.items() for a in v}
BODY_SECTIONS = ["experience", "projects", "leadership"]

SECTION_POINTS = {"education": 3, "projects": 3, "skills": 2, "awards": 1, "memberships": 1, "certifications": 1}
PAIR_POINTS = 4          # experience + leadership, best of the two
ORDER_MAX_DEDUCTION = 2

CLICHES = ["passionate", "results-driven", "results driven", "results-oriented", "proven track record", "hard-working", "hardworking",
           "team player", "self-motivated", "detail-oriented", "detail oriented", "go-getter", "dynamic", "seasoned", "think outside the box",
           "fast learner", "quick learner", "highly motivated", "excellent communication skills", "strong work ethic", "self-starter",
           "motivated individual", "ambitious", "dedicated", "good interpersonal skills", "willing to learn", "synergy"]

WEAK_PHRASES = ["responsible for", "helped with", "helped to", "assisted with", "assisted in", "worked on", "duties included",
                "tasked with", "in charge of"]
WEAK_STARTS = {"responsible", "helped", "help", "assisted", "assist", "worked", "work", "duties", "tasked", "involved", "participated",
               "part", "in", "member", "was", "were", "did", "have", "had", "my", "the", "a", "an", "i"}

ACTION_VERBS = set("""achieved analysed analyzed assembled audited began budgeted built campaigned captained chaired championed coached coded
collaborated compiled conducted coordinated counselled created curated debugged delivered deployed designed developed directed documented drafted
drove edited engineered established evaluated executed fabricated facilitated forecast founded generated grew guided handled hosted identified
implemented improved increased initiated introduced launched led managed mentored mobilised mobilized moderated modelled negotiated optimised
optimized organised organized oversaw piloted planned presented produced programmed promoted prototyped published raised ran recruited redesigned
reduced represented researched resolved restructured reviewed scheduled secured served simulated sold spearheaded spoke streamlined supervised
surveyed taught tested tracked trained translated tutored visualised visualized volunteered won wrote made""".split())
IRREGULAR_PAST = {"led": "lead", "built": "build", "ran": "run", "won": "win", "wrote": "write", "taught": "teach", "drove": "drive",
                  "made": "make", "grew": "grow", "spoke": "speak", "began": "begin", "sold": "sell"}
RESULT_WORDS = ["increased", "reduced", "improved", "raised", "grew", "saved", "won", "achieved", "reaching", "reached", "resulting", "resulted",
                "which", "boosted", "doubled", "tripled", "secured", "earned", "awarded", "ranked", "placed", "delivered", "launched",
                "published", "selected"]

CASUAL_EMAIL_WORDS = ["boy", "girl", "baby", "babe", "cute", "sweet", "king", "queen", "lover", "cool", "handsome", "pretty", "prince",
                      "princess", "sexy", "swag", "gangster", "angel", "dollar", "money", "baddest", "slim", "chic"]

TARGET_KEYWORDS = {
    "internship": ["intern", "siwes", "industrial training", "placement", "hands-on", "excel", "python", "data", "communication", "team", "project", "technical"],
    "scholarship": ["cgpa", "gpa", "first class", "second class upper", "distinction", "award", "scholar", "dean's list", "merit", "competition", "published", "research", "community", "volunteer", "leadership"],
    "graduate study": ["research", "thesis", "dissertation", "publication", "published", "supervis", "laborator", "cgpa", "gpa", "first class", "second class", "seminar", "conference", "academic", "project"],
    "leadership": ["led", "lead", "president", "chair", "coordinator", "founder", "founded", "captain", "organis", "organiz", "mentor", "volunteer", "team of", "managed", "committee", "executive", "initiated"],
}

CITIES = ["lagos", "abuja", "ibadan", "kano", "port harcourt", "enugu", "kaduna", "benin city", "ilorin", "akure", "abeokuta", "owerri", "jos",
          "calabar", "uyo", "nsukka", "zaria", "ile-ife", "ife", "yola", "maiduguri", "awka", "asaba", "warri", "sokoto", "minna", "makurdi",
          "lokoja", "osogbo", "ado-ekiti", "nairobi", "accra", "kumasi", "kampala", "kigali", "dar es salaam", "addis ababa", "johannesburg",
          "cape town", "dakar", "cairo", "lusaka", "harare", "lome", "cotonou", "abidjan", "freetown", "monrovia", "banjul", "gaborone", "windhoek"]

CITIES += ["minna", "bauchi", "gombe", "abakaliki", "umuahia", "yenagoa", "dutse", "katsina", "lafia", "jalingo", "damaturu", "gusau", "birnin kebbi",
           "ado ekiti", "ikeja", "lekki", "ota", "sagamu", "ikorodu", "suleja", "kubwa", "gwagwalada", "lagos island"]
PLACES = ["Nigeria", "Ghana", "Kenya", "Uganda", "Rwanda", "Tanzania", "Ethiopia", "South Africa", "Senegal", "Cameroon", "Egypt", "Zambia",
          "Zimbabwe", "Lagos", "Oyo", "Ogun", "Kano", "Kaduna", "Rivers", "Enugu", "Niger", "Plateau", "Delta", "Edo", "FCT", "Abuja", "Ondo", "Osun",
          "Kwara", "Anambra", "Imo", "Abia", "Benue", "Borno", "Bauchi", "Cross River", "Akwa Ibom", "Ekiti", "Kogi", "Nasarawa", "Sokoto", "Taraba", "Yobe", "Zamfara"]
