import pandas as pd
import numpy as np
import random


def flip(p: float) -> int:
    """Return 1 with probability p."""
    return 1 if random.random() < p else 0


def generate_patient_data():
    # --- Baseline demographic & behavior ---
    patient = {
        "age": random.randint(15, 55),
        "new_partners_last_3_months": random.randint(0, 5),
        "condom_use_consistency": random.choice(["always", "sometimes", "never"]),

        # --- Symptom placeholders ---
        "dysuria": 0,
        "urinary_frequency": 0,
        "urinary_urgency": 0,
        "discharge_thin": 0,
        "discharge_thick": 0,
        "discharge_yellow_green": 0,
        "odor_fishy": 0,
        "itching": 0,
        "spotting": 0,
        "abdominal_pain": 0,
        "pelvic_pain": 0,
        "ulcers_painful": 0,
        "ulcer_painless": 0,
        "rash_palm_sole": 0,
        "blisters_genital": 0,
        "fever": 0,
        "fatigue": 0,
        "weight_loss": 0,
        "swollen_lymph_nodes": 0,
        "jaundice": 0,
        "sore_throat": 0,
        "is_asymptomatic": 0,
    }

    # --- Diagnosis list ---
    conditions = [
        "Healthy", "Chlamydia", "Gonorrhea", "Syphilis", "Herpes",
        "HPV", "HIV", "Hepatitis B", "Hepatitis C", "Trichomoniasis",
        "Mycoplasma genitalium", "BV", "UTI", "PID", "Pubic Lice", "Scabies"
    ]

    # --- Probability weights ---
    weights = [0.02, 0.14, 0.11, 0.08, 0.08, 0.10, 0.06, 0.05, 0.04,
               0.05, 0.04, 0.05, 0.04, 0.03, 0.02, 0.02]

    ground_truth = random.choices(conditions, weights, k=1)[0]
    patient["ground_truth"] = ground_truth

    # --- Healthy: clear all symptoms ---
    if ground_truth == "Healthy":
        for s in patient.keys():
            if s not in ["age", "new_partners_last_3_months", "condom_use_consistency", "ground_truth"]:
                patient[s] = 0
        patient["is_asymptomatic"] = 1
        return patient

    # --- STD / infection profiles ---
    if ground_truth == "Chlamydia":
        if flip(0.20):
            patient["is_asymptomatic"] = 1
        else:
            patient["dysuria"] = 1
            patient["discharge_thin"] = 1
            patient["odor_fishy"] = flip(0.05)
            patient["spotting"] = flip(0.50)
            patient["abdominal_pain"] = flip(0.60)
            patient["pelvic_pain"] = flip(0.40)

    elif ground_truth == "Gonorrhea":
        if flip(0.20):
            patient["is_asymptomatic"] = 1
        else:
            patient["dysuria"] = 1
            patient["discharge_thick"] = 1
            patient["discharge_yellow_green"] = 1
            patient["abdominal_pain"] = flip(0.40)
            patient["sore_throat"] = flip(0.20)

    elif ground_truth == "Syphilis":
        r = random.random()
        if r < 0.6:
            patient["ulcer_painless"] = 1
            patient["swollen_lymph_nodes"] = flip(0.50)
        elif r < 0.9:
            patient["rash_palm_sole"] = 1
            patient["fever"] = flip(0.50)
            patient["fatigue"] = flip(0.50)
            patient["swollen_lymph_nodes"] = flip(0.60)
        else:
            patient["is_asymptomatic"] = 1

    elif ground_truth == "Herpes":
        if flip(0.30):
            patient["is_asymptomatic"] = 1
        else:
            patient["ulcers_painful"] = 1
            patient["blisters_genital"] = 1
            patient["fever"] = flip(0.30)
            patient["swollen_lymph_nodes"] = flip(0.40)

    elif ground_truth == "HPV":
        if flip(0.65):
            patient["is_asymptomatic"] = 1
        else:
            patient["itching"] = 1
            patient["spotting"] = flip(0.30)

    elif ground_truth == "HIV":
        if flip(0.40):
            patient["is_asymptomatic"] = 1
        else:
            patient["fever"] = 1
            patient["fatigue"] = 1
            patient["swollen_lymph_nodes"] = 1
            patient["sore_throat"] = flip(0.30)
            patient["weight_loss"] = flip(0.40)

    elif ground_truth == "Hepatitis B":
        if flip(0.35):
            patient["is_asymptomatic"] = 1
        else:
            patient["jaundice"] = flip(0.70)
            patient["fatigue"] = 1
            patient["fever"] = flip(0.40)
            patient["abdominal_pain"] = flip(0.50)

    elif ground_truth == "Hepatitis C":
        if flip(0.50):
            patient["is_asymptomatic"] = 1
        else:
            patient["jaundice"] = flip(0.50)
            patient["fatigue"] = 1
            patient["abdominal_pain"] = flip(0.50)

    elif ground_truth == "Trichomoniasis":
        if flip(0.20):
            patient["is_asymptomatic"] = 1
        else:
            patient["itching"] = 1
            if flip(0.70):
                patient["discharge_thin"] = 1
            else:
                patient["discharge_yellow_green"] = 1
            patient["odor_fishy"] = flip(0.50)
            patient["dysuria"] = flip(0.40)
            patient["abdominal_pain"] = flip(0.40)

    elif ground_truth == "Mycoplasma genitalium":
        if flip(0.30):
            patient["is_asymptomatic"] = 1
        else:
            patient["dysuria"] = 1
            patient["discharge_thin"] = 1
            patient["spotting"] = flip(0.40)
            patient["pelvic_pain"] = flip(0.50)
            patient["abdominal_pain"] = flip(0.40)

    elif ground_truth == "BV":
        if flip(0.15):
            patient["is_asymptomatic"] = 1
        else:
            patient["discharge_thin"] = 1
            patient["odor_fishy"] = 1
            patient["itching"] = flip(0.60)
            patient["dysuria"] = 0

    elif ground_truth == "UTI":
        if flip(0.05):
            patient["is_asymptomatic"] = 1
        else:
            patient["dysuria"] = 1
            patient["urinary_frequency"] = 1
            patient["urinary_urgency"] = 1
            patient["abdominal_pain"] = flip(0.50)

    elif ground_truth == "PID":
        patient["pelvic_pain"] = 1
        patient["abdominal_pain"] = 1
        patient["fever"] = flip(0.40)
        patient["discharge_thick"] = flip(0.40)
        patient["spotting"] = flip(0.30)
        patient["dysuria"] = flip(0.30)

    elif ground_truth == "Pubic Lice":
        patient["itching"] = 1

    elif ground_truth == "Scabies":
        patient["itching"] = 1

    return patient


if __name__ == "__main__":
    num_patients = 25000
    print(f"Generating {num_patients} patient records...")

    data = [generate_patient_data() for _ in range(num_patients)]
    df = pd.DataFrame(data)

    # Encode condom_use_consistency
    df = pd.get_dummies(df, columns=["condom_use_consistency"], drop_first=True)

    output_filename = "synthetic_data.csv"
    df.to_csv(output_filename, index=False)

    print(f"\nSuccessfully generated {num_patients} samples to '{output_filename}'")
    print("\nLabel distribution (%):")
    print(df["ground_truth"].value_counts(normalize=True).round(3))
