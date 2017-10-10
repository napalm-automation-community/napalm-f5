# Define threshold for alerts (70%) of critical value.
ALERT = 0.7

# Define Family / Platform sensors' locations and critical levels.
LIMITS = {
    'VIPRION_A114': {
        # Chassis sensors,
        '1': (65, 'Annunciator inlet'),
        '2': (65, 'Annunciator outlet'),
        '3': (65, 'Annunciator 2 inlet'),
        '4': (65, 'Annunciator 2 outlet'),
        '5': (70, 'Fan tray inlet'),
        '6': (70, 'Fan tray outlet'),
        '7': (70, 'Fan tray 2 inlet'),
        '8': (70, 'Fan tray 2 outlet'),
        # Blade temperature sensors
        'Host inlet local': (50, 'Host inlet local'),
        'Host inlet remote': (45, 'Host inlet remote'),
        'Host outlet local': (78, 'Host outlet local'),
        'Host outlet remote': (52, 'Host outlet remote'),
        'Host Trident': (83, 'Host Trident'),
        'Host Trident remote': (83, 'Host Trident remote'),
        'Mezz. HSBe 1': (91, 'Mezz. HSBe 1'),
        'Mezz. HSBe 2': (91, 'Mezz. HSBe 2'),
        'Mezz. Tmp421 local 1': (65, 'Mezz. Tmp421 local 1'),
        'Mezz. Tmp421 local 2': (65, 'Mezz. Tmp421 local 2'),
    },
    '12000_D111': {
        '1': (73, 'Main board HSBE transistor temperature'),
        '2': (56, 'Main board HSBE IC temperature'),
        '3': (40, 'Main board inlet transistor temperature'),
        '4': (58, 'Main board inlet IC temperature'),
        '5': (64, 'Main board outlet transistor temperature'),
        '6': (64, 'Main board outlet IC temperatures'),
        '7': (67, 'Power supply #1 meas. inlet temperature'),
        '8': (67, 'Power supply #2 meas. inlet temperature'),
        '9': (60, 'PECI-Bridge local temperature'),
        '10': (74, 'Mezzanine board HSBE transistor temperature'),
        '11': (57, 'Mezzanine board HSBE IC temperature'),
        '12': (66, 'Main board near Trident (B56843) temperature'),
        '13': (68, 'Nitrox3x3 outlet transistor temperature'),
        '14': (72, 'Nitrox3x3 outlet IC temperature'),
    }
}
