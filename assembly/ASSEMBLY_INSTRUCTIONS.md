# Assembly instructions

## BOM

### Electronics

1. **CSN-A2 Micro panel printer** (ESC/POS,9V/12V)
   ![](assets\CSN-A2_micro_panel_printer.png)
   **Spec:** https://cdn-shop.adafruit.com/datasheets/CSN-A2+User+Manual.pdf
   **Shop:** https://ali.click/gpp8018
2. **Raspberry Pi Zero W**
   ![](assets\rpi_zero_w.png)
   **Spec:** https://cdn.sparkfun.com/assets/learn_tutorials/6/7/6/PiZero_1.pdf
   **Shop:** https://ali.click/dmq801y
3. **Kis-3r33s DC-DC Step-Down Power Module**
   ![](assets\kis-3r33s_DC-DC_step-down.png)
   **Spec:** https://www.datasheetcafe.com/wp-content/uploads/2016/05/KIS-3R33S.pdf
   **Shop:** https://ali.click/ker801a
4. **USB Type-C QC/PD/AFC Trigger-Decoy Board module** (5V, 9V, 12V, 15V, 20V)
   ![](assets\type-c_PD_trigger.png)
   **Spec:** https://manuals.plus/asin/B0CDWXN1WR
   **Shop:** https://ali.click/p1t8018
5. **2,4Hhz Wi-Fi antenna 2dBi RP-SMA**
   ![](assets\RP-SMA_wifi_antenna.png)
   **Shop:** https://ali.click/ort801m

### Fasteners

1. m3 x 4mm bolts (round head or flat head) - 13 pcs
2. m2.5 x 5mm bolts - 2 pcs
3. m3 x 4mm Threaded insert - 4 pcs
4. m3 x 4mm Threaded insert - 4 pcs

### Wires

24 AWG wires: red,black ~15 cm

28 AWG wires: red,black, green, yellow ~ 10 cm

### Power supply

Qick charge power supply that supports PD/QC 12V output by PD trigger

### Tools

* Mini side nippers
* Сyanoacrylate glue
* Allen keys

## Electronic parts wiring

### Schematic

![](assets\schematic.png)

### Instruction

1. Switch the "USB Type-C QC/PD/AFC Trigger-Decoy Board module" to 12V mode, as shown in the diagram on the back of the board.
2. Directly connect the PD-Trigger module's outputs (VCC out, GND out) to the printer's power connector (GND, VH input).
3. Using another pair of wires, connect the PD-Trigger module's outputs (VCC out, GND out) to the input of the "Kis-3r33s DC-DC Step-Down Power Module": GND out -> IN-, VCC out -> IN+.
4. Connect the "Kis-3r33s DC-DC Step-Down Power Module" outputs to the Raspberry Pi Zero W's GPIO power pins: OUT+ -> Rpi PIN 2 (+5V), OUT- -> Rpi PIN 6 (GND).
   > Caution! Be careful with power supply polarity reversal! The Rpi does not have reverse polarity protection on its GPIO ports.
   >
5. Connect the CSN-A2 printer's TTL connector to the Raspberry Pi Zero W's GPIO pins: Printer RXD (receive data) -> Rpi PIN 8 (TXD), Printer TXD (send data) -> Rpi PIN 10 (RXD), Printer TTL GND -> Rpi PIN 14 (GND).

## Case 3D printing


![](assets\render_1.png)

![](assets\print_prepare.png)

### 3D Models

Model for printing and customization: Printer Case.step
Project for Bambulab Studio with a profile for Babulab X1C: Printer Case.3mf
Files are located in the following folder: assembly/3D_printing/

### Printing parameters

* Material: PLA
* Layer height: 0.08
* Walls: 3
* Top layers: 9
* Bottom layers: 7
* Infill: 15%
* Supports: yes (normal + snug)

> Use brim to print small parts like legs. Apply glue to connect legs to case.
