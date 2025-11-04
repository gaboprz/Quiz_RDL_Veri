En este documento se especifican los comandos utilizados para ejecutar los distintos códigos.

Paso 1:
- Generar rtl: peakrdl regblock peakrdl_manual.rdl -o generated_rtl
- Generar uvm: peakrdl uvm peakrdl_manual.rdl -o generated_uvm
- Generar html: peakrdl html peakrdl_manual.rdl -o generated_html

Paso 2:
- Se ajusta el contenido del excel a los registros del Aligner

Paso 3:
- Se genera un código de python que parsea el excel a un rtl. Se realiza con ayuda de Cloude.
- Generar rtl: python parseo_excel.py register_spec_multi_block.xlsx peakrdl_python.rdl

Paso 4:
- Generar rtl: peakrdl regblock peakrdl_python.rdl -o generated_rtl
- Generar uvm: peakrdl uvm peakrdl_python.rdl -o generated_uvm
- Generar html: peakrdl html peakrdl_python.rdl -o generated_html