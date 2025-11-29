import csv
from dataclasses import dataclass
from typing import List


@dataclass
class BearingParams:
    d: float
    D: float
    C_0: float  # C_0r in CSV
    C: float  # C_r in CSV
    c: float
    T: float
    a: float
    e: float
    Y_0: float  # Y0 in CSV
    Y: float  # Y1 in CSV
    name: str
    da_min: float 
    da_max: float 


def read_bearings_from_csv(filename: str) -> List[BearingParams]:
    """Read bearing parameters from CSV file."""
    bearings = []
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bearing = BearingParams(
                d=float(row['d']),
                D=float(row['D']),
                C_0=float(row['C_0r']),
                C=float(row['C_r']),
                a=float(row['a']) / 1000,  # Convert mm to m
                e=float(row['e']),
                Y_0=float(row['Y0']),
                Y=float(row['Y1']),
                name=str(row['name']),
                c =float(row['C']) / 1000,
                T = float(row['T']) / 1000,
                da_min = float(row['da_min']),
                da_max = float(row['da_max']))

            bearings.append(bearing)
    return bearings


def calculate_bearing_loads(bearing_C: BearingParams,
                            bearing_D: BearingParams):
    """Calculate bearing loads for a given combination of bearings."""

    f2f = True
    # Extract parameters for bearing D
    Y_D_0 = bearing_D.Y_0
    Y_D = bearing_D.Y
    T_D = bearing_D.T
    a_D = bearing_D.a
    e_D = bearing_D.e
    C_0_D = bearing_D.C_0
    C_D = bearing_D.C

    # Extract parameters for bearing C
    Y_C_0 = bearing_C.Y_0
    Y_C = bearing_C.Y
    a_C = bearing_C.a
    T_C = bearing_C.T
    e_C = bearing_C.e
    C_0_C = bearing_C.C_0
    C_C = bearing_C.C

    # dimensions to start of bearing
    d_c_prime = 0.27
    d_d_prime = 0.078
    if f2f == True:
        d_C=d_c_prime-a_C + bearing_C.c
        d_D = d_d_prime-a_D+ bearing_D.c
    else:
        d_C = d_c_prime + a_C
        d_D = d_d_prime + a_D

    r = 0.07  # 70 mm

    W_r_p1 = 3.651 * 10**3
    W_z_p1 = 2.282 * 10**3
    W_t_p1 = 11.829 * 10**3

    Dx = (-d_C * W_r_p1 - r * W_z_p1) / (d_C + d_D)
    Dy = (d_C * W_t_p1) / (d_C + d_D)

    Cx = -W_r_p1 - Dx
    Cy = W_t_p1 - Dy

    Dr = (Dx**2 + Dy**2)**0.5
    Cr = (Cx**2 + Cy**2)**0.5

    Fae = W_z_p1

    if f2f == True:
        factor = Fae + 0.6 / Y_C * Cr
        if factor >= 0.6 / Y_D * Dr:
            Dz = factor
            Cz = 0
        else:
            Dz = 0
            Cz = 0.6 / Y_D * Dr - Fae
    else:
        factor = Fae + 0.6 / Y_D * Dr
        if factor >= 0.6 / Y_C * Cr:
            Cz = factor
            Dz = 0
        else:
            Cz = 0
            Dz = 0.6 / Y_C * Cr - Fae

    # static load
    # for d
    P_d_0 = max(Dr, 0.5 * Dr + Y_D_0 * Dz)

    # for c
    P_c_0 = max(Cr, 0.5 * Cr + Y_C_0 * Cz)

    # dynamic load
    # for d
    P_d = Dr if Dz / Dr <= e_D else 0.4 * Dr + Y_D * Dz

    # for C
    P_c = Cr if Cz / Cr <= e_C else 0.4 * Cr + Y_C * Cz

    f_s_D = C_0_D / P_d_0
    f_s_C = C_0_C / P_c_0

    L_10_D = (C_D / P_d)**(10 / 3)
    L_10_C = (C_C / P_c)**(10 / 3)

    return {
        'f_s_D': f_s_D,
        'L_10_D': L_10_D,
        'f_s_C': f_s_C,
        'L_10_C': L_10_C,
        'P_d_0': P_d_0,
        'P_c_0': P_c_0,
        'P_d': P_d,
        'P_c': P_c
    }


def main():
    # Read all bearings from CSV
    bearings = read_bearings_from_csv('bearing_specifications.csv')

    print(f"Loaded {len(bearings)} bearings from data.csv")
    print(f"Testing {len(bearings) * len(bearings)} combinations...")

    # Open output CSV file for writing
    with open('results.csv', 'w', newline='') as csvfile:
        fieldnames = [
            'Bearing_C_d', 'Bearing_C_D', 'Bearing_C_C_0', 'Bearing_C_C','Bearing_C_c','Bearing_C_T','Bearing_C_Name',
            'Bearing_D_d', 'Bearing_D_D', 'Bearing_D_C_0', 'Bearing_D_C','Bearing_D_Name', 'Bearing_D_c','Bearing_D_T',
            'f_s_D', 'L_10_D', 'f_s_C', 'L_10_C', 'P_d_0', 'P_c_0', 'P_d', 'C_da_min', 'D_da_min','P_c'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        # Test every combination of bearings
        combination_count = 0
        valid_count = 0
        for bearing_C in bearings:
            for bearing_D in bearings:
                results = calculate_bearing_loads(bearing_C, bearing_D)

                combination_count += 1
                
                # Filter: only keep results where f_s > 20 and L_10 > 50000 for both bearings
                if (results['f_s_D'] > 20 and results['f_s_C'] > 20 and 
                   results['L_10_D'] > 50000 and results['L_10_C'] > 50000 and bearing_C.d <=66 and bearing_D.da_min <=86 ):
                    
                # Write row to CSV
                    writer.writerow({
                        'Bearing_C_d': bearing_C.d,
                        'Bearing_C_D': bearing_C.D,
                        'Bearing_C_C_0': bearing_C.C_0,
                        'Bearing_C_C': bearing_C.C,
                        'Bearing_C_c': bearing_C.c,
                        'Bearing_C_T': bearing_C.T,
                        'Bearing_C_Name': bearing_C.name,
                        'Bearing_D_d': bearing_D.d,
                        'Bearing_D_D': bearing_D.D,
                        'Bearing_D_C_0': bearing_D.C_0,
                        'Bearing_D_C': bearing_D.C,
                        'Bearing_D_c': bearing_D.c,
                        'Bearing_D_T': bearing_D.T,
                        'Bearing_D_Name': bearing_D.name,
                        'f_s_D': results['f_s_D'],
                        'L_10_D': results['L_10_D'],
                        'f_s_C': results['f_s_C'],
                        'L_10_C': results['L_10_C'],
                        'P_d_0': results['P_d_0'],
                        'P_c_0': results['P_c_0'],
                        'P_d': results['P_d'],
                        'P_c': results['P_c'],
                        'C_da_min':bearing_C.da_min,
                        'D_da_min':bearing_D.da_min
                    })
                    valid_count += 1

        print(f"Completed! Tested {combination_count} combinations.")
        print(f"Valid combinations (f_s > 20 and L_10 > 50,000): {valid_count}")
        print(f"Results written to results.csv")


if __name__ == "__main__":
    main()

# left 66 right 86 