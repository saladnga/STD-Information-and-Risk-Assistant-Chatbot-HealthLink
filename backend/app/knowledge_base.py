STD_KNOWLEDGE = {
    "Healthy": {
        "full_name": "No STI Detected",
        "description": "No specific STI suggested by current symptoms, but testing may be appropriate depending on exposure.",
        "symptoms": [],
        "treatment": "No treatment needed. Consider screening if exposed or unsure.",
        "complications": "None related to STI.",
        "prevention": [
            "Use condoms consistently",
            "Regular STI screening",
            "Limit number of partners",
            "Open communication with partners"
        ],
        "when_to_test": "Test if you've had unprotected sex, new partners, or symptoms develop.",
        "urgency": "low"
    },

    "Chlamydia": {
        "full_name": "Chlamydia trachomatis Infection",
        "description": "Common bacterial STI; frequently asymptomatic, especially in females.",
        "symptoms": [
            "Often asymptomatic",
            "Abnormal vaginal/penile discharge (usually thin)",
            "Burning sensation when urinating",
            "Lower abdominal or pelvic pain",
            "Bleeding between periods"
        ],
        "treatment": "Antibiotics (e.g., doxycycline or azithromycin). Treat partners and abstain until completion.",
        "complications": "Pelvic inflammatory disease (PID), infertility, ectopic pregnancy, epididymitis.",
        "prevention": [
            "Use condoms consistently",
            "Regular screening (especially <25 years or with new partners)",
            "Limit number of partners"
        ],
        "when_to_test": "Screen annually for sexually active persons at risk; test after unprotected sex or exposure.",
        "urgency": "high"
    },

    "Gonorrhea": {
        "full_name": "Neisseria gonorrhoeae Infection",
        "description": "Bacterial STI that can infect genitals, rectum, and throat.",
        "symptoms": [
            "Often asymptomatic (especially in females)",
            "Thick yellow/green discharge",
            "Painful or burning urination",
            "Pelvic/abdominal pain",
            "Sore throat (oral exposure)"
        ],
        "treatment": "Ceftriaxone injection as first-line; treat partners and abstain until completion.",
        "complications": "PID, infertility, disseminated gonococcal infection (arthritis, rash).",
        "prevention": [
            "Use condoms consistently",
            "Regular STI screening",
            "Limit number of partners"
        ],
        "when_to_test": "Test with symptoms, after exposure, or if partner is positive.",
        "urgency": "high"
    },

    "Syphilis": {
        "full_name": "Treponema pallidum (Syphilis)",
        "description": "Multistage bacterial STI: primary (painless chancre), secondary (rash), latent, and tertiary.",
        "symptoms": [
            "Painless sore (chancre) at exposure site",
            "Rash on palms/soles, swollen lymph nodes, fever (secondary)",
            "Often asymptomatic in latent stage"
        ],
        "treatment": "Benzathine penicillin G per stage; treat partners, follow serologic monitoring.",
        "complications": "Neurologic, cardiovascular syphilis, adverse pregnancy outcomes (congenital syphilis).",
        "prevention": [
            "Condom use",
            "Regular screening for high-risk groups",
            "Avoid sex until sores are healed and treatment completed"
        ],
        "when_to_test": "Any genital sore/rash, known exposure, or pregnancy screening per guidelines.",
        "urgency": "high"
    },

    "Herpes": {
        "full_name": "Genital Herpes (HSV-1/HSV-2)",
        "description": "Viral STI causing recurrent painful blisters/ulcers; many are asymptomatic.",
        "symptoms": [
            "Painful blisters or ulcers",
            "Tingling/itching prodrome",
            "Dysuria with lesions",
            "Flu-like symptoms in first outbreak",
            "Often asymptomatic"
        ],
        "treatment": "Antivirals (acyclovir/valacyclovir) reduce severity, duration, and transmission risk.",
        "complications": "Recurrent outbreaks, increased HIV susceptibility, neonatal herpes if transmitted during birth.",
        "prevention": [
            "Condoms (risk reduced, not eliminated)",
            "Avoid sexual contact during outbreaks",
            "Suppressive therapy for frequent recurrences"
        ],
        "when_to_test": "Test when ulcers/sores present or if partner has herpes; consider type-specific serology.",
        "urgency": "moderate"
    },

    "HPV": {
        "full_name": "Human Papillomavirus",
        "description": "Very common viral STI; many types are asymptomatic. Some cause warts or cancers.",
        "symptoms": [
            "Often asymptomatic",
            "Genital warts (some types)",
            "Abnormal Pap test (cervical changes)"
        ],
        "treatment": "Warts: topical therapy, cryotherapy, or procedures. No antiviral cure; many infections clear spontaneously.",
        "complications": "Cervical, anal, penile, vulvar, and oropharyngeal cancers (high-risk types).",
        "prevention": [
            "HPV vaccination per age guidelines",
            "Condoms (partial protection)",
            "Regular cervical screening (Pap/HPV tests)"
        ],
        "when_to_test": "Per cervical screening guidelines; evaluate visible warts.",
        "urgency": "moderate"
    },

    "HIV": {
        "full_name": "Human Immunodeficiency Virus",
        "description": "Retroviral infection that weakens the immune system over time; treatable with ART.",
        "symptoms": [
            "Acute phase: fever, sore throat, fatigue, lymphadenopathy",
            "Often asymptomatic for years without ART",
            "Unintended weight loss (later)"
        ],
        "treatment": "Antiretroviral therapy (ART) for all persons with HIV; near-normal lifespan with adherence.",
        "complications": "Opportunistic infections, AIDS-defining illnesses if untreated.",
        "prevention": [
            "Condoms and safer sex",
            "Pre-exposure prophylaxis (PrEP) for those at risk",
            "Post-exposure prophylaxis (PEP) after high-risk exposure"
        ],
        "when_to_test": "Routine screening per guidelines; immediately after high-risk exposure (and again at window periods).",
        "urgency": "urgent"
    },

    "Hepatitis B": {
        "full_name": "Hepatitis B Virus (HBV)",
        "description": "Viral infection of the liver transmitted via blood/sex; vaccine-preventable.",
        "symptoms": [
            "Often asymptomatic",
            "Fatigue, fever",
            "Jaundice, dark urine",
            "Abdominal discomfort"
        ],
        "treatment": "Acute HBV: supportive. Chronic HBV: antiviral therapy in selected cases; regular liver monitoring.",
        "complications": "Chronic hepatitis, cirrhosis, hepatocellular carcinoma.",
        "prevention": [
            "HBV vaccination",
            "Condom use",
            "Avoid sharing needles/sharps"
        ],
        "when_to_test": "After exposure, abnormal liver tests, or per prenatal and risk-based screening.",
        "urgency": "moderate"
    },

    "Hepatitis C": {
        "full_name": "Hepatitis C Virus (HCV)",
        "description": "Viral hepatitis transmitted mainly via blood; sexual transmission can occur.",
        "symptoms": [
            "Often asymptomatic",
            "Fatigue",
            "Jaundice (less common acutely)",
            "Abdominal pain"
        ],
        "treatment": "Direct-acting antivirals (DAAs) can cure most chronic HCV infections.",
        "complications": "Chronic hepatitis, cirrhosis, hepatocellular carcinoma.",
        "prevention": [
            "Avoid needle sharing",
            "Condoms for risk reduction",
            "Screening for those with risk factors"
        ],
        "when_to_test": "One-time screening for adults per guidelines; test after exposure or abnormal liver tests.",
        "urgency": "moderate"
    },

    "Trichomoniasis": {
        "full_name": "Trichomonas vaginalis Infection",
        "description": "Parasitic STI; often causes itching and discharge, especially in females.",
        "symptoms": [
            "Itching or irritation",
            "Thin or yellow-green discharge",
            "Fishy odor (sometimes)",
            "Dysuria, dyspareunia"
        ],
        "treatment": "Metronidazole or tinidazole (single or multi-day regimens). Treat partners and abstain until completion.",
        "complications": "Adverse pregnancy outcomes, increased susceptibility to other STIs.",
        "prevention": [
            "Condom use",
            "Limit number of partners",
            "Prompt treatment of partners"
        ],
        "when_to_test": "Test if symptomatic or after exposure; consider screening in high-prevalence settings.",
        "urgency": "moderate"
    },

    "Mycoplasma genitalium": {
        "full_name": "Mycoplasma genitalium Infection",
        "description": "Emerging bacterial STI associated with urethritis, cervicitis, and PID; resistance is common.",
        "symptoms": [
            "Often asymptomatic",
            "Dysuria",
            "Thin discharge",
            "Pelvic or lower abdominal pain",
            "Spotting"
        ],
        "treatment": "Guideline-based multi-step antibiotics (e.g., doxycycline then moxifloxacin; local resistance may vary).",
        "complications": "PID, infertility risk (under study), persistent urethritis/cervicitis.",
        "prevention": [
            "Condom use",
            "Partner management",
            "Targeted testing in persistent symptoms"
        ],
        "when_to_test": "Consider in persistent/recurrent urethritis or cervicitis after common causes excluded.",
        "urgency": "moderate"
    },

    "BV": {
        "full_name": "Bacterial Vaginosis",
        "description": "Imbalance of vaginal flora; not strictly an STI but associated with sexual activity.",
        "symptoms": [
            "Thin gray/white/green discharge",
            "Foul-smelling 'fishy' vaginal odor",
            "Vaginal itching",
            "Burning during urination"
        ],
        "treatment": "Antibiotics (metronidazole or clindamycin). Complete full course.",
        "complications": "Higher risk of STIs, pregnancy complications, and PID.",
        "prevention": [
            "Avoid douching",
            "Limit number of sex partners",
            "Use condoms consistently"
        ],
        "when_to_test": "If symptomatic; diagnosis via vaginal fluid tests.",
        "urgency": "moderate"
    },

    "UTI": {
        "full_name": "Urinary Tract Infection",
        "description": "Bacterial infection of the urinary tract; not an STI, but symptoms can overlap.",
        "symptoms": [
            "Strong, persistent urge to urinate",
            "Burning with urination",
            "Frequent small-volume urination",
            "Cloudy or strong-smelling urine",
            "Pelvic pain"
        ],
        "treatment": "Antibiotics; hydration; consider preventive measures for recurrent UTIs.",
        "complications": "Pyelonephritis (kidney infection) if untreated.",
        "prevention": [
            "Hydration",
            "Urinate after sex",
            "Wipe front to back",
            "Avoid irritating products"
        ],
        "when_to_test": "If symptoms last >48 hours, with fever/flank pain, or recurrent episodes.",
        "urgency": "moderate"
    },

    "PID": {
        "full_name": "Pelvic Inflammatory Disease",
        "description": "Infection/inflammation of female upper genital tract, often from untreated STIs.",
        "symptoms": [
            "Lower abdominal and pelvic pain",
            "Fever",
            "Abnormal discharge",
            "Spotting or postcoital bleeding",
            "Dyspareunia"
        ],
        "treatment": "Broad-spectrum antibiotics per guidelines; consider hospitalization if severe.",
        "complications": "Infertility, chronic pelvic pain, ectopic pregnancy.",
        "prevention": [
            "Timely treatment of STIs",
            "Condom use",
            "Routine screening"
        ],
        "when_to_test": "Evaluate urgently with pelvic pain plus cervical motion/uterine/adnexal tenderness.",
        "urgency": "urgent"
    },

    "Pubic Lice": {
        "full_name": "Pediculosis pubis (Pubic Lice)",
        "description": "Infestation of pubic hair with lice, spread by close contact.",
        "symptoms": [
            "Intense itching in pubic area",
            "Visible nits or lice on hairs",
            "Irritation or excoriations"
        ],
        "treatment": "Topical pediculicides (permethrin/pyrethrin); wash linens/clothes; treat partners.",
        "complications": "Secondary skin infection from scratching.",
        "prevention": [
            "Avoid sharing bedding/towels",
            "Treat partners simultaneously"
        ],
        "when_to_test": "Clinical inspection if itching/visible nits; consider STI screening due to co-exposures.",
        "urgency": "low"
    },

    "Scabies": {
        "full_name": "Scabies (Sarcoptes scabiei)",
        "description": "Skin infestation causing intense nocturnal itching; spread by prolonged close contact.",
        "symptoms": [
            "Severe itching (worse at night)",
            "Burrows, papules in finger webs, wrists, genitals",
            "Excoriations from scratching"
        ],
        "treatment": "Topical permethrin 5% (repeat in 7 days) or oral ivermectin per guidelines; treat close contacts; decontaminate linens.",
        "complications": "Secondary bacterial infection; crusted scabies in immunocompromised.",
        "prevention": [
            "Treat all close contacts",
            "Wash/dry linens and clothing on hot cycles"
        ],
        "when_to_test": "Clinical evaluation if typical rash/itching; consider skin scrapings in uncertain cases.",
        "urgency": "moderate"
    }
}
