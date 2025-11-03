import pandas as pd
import sys

def access_to_rdl(access_type):
    """
    Convierte el tipo de acceso a formato RDL.
    
    Parámetros:
        access_type: string con el tipo de acceso (rw, ro, wo, w1c)
    
    Retorna:
        tupla (sw_access, onwrite) donde:
        - sw_access: tipo de acceso para software
        - onwrite: comportamiento especial al escribir (o None)
    """
    access_map = {
        'rw': ('rw', None),      # Read-Write
        'ro': ('r', None),        # Read-Only
        'wo': ('w', None),        # Write-Only
        'w1c': ('w', 'woclr')    # Write-1-to-Clear
    }
    return access_map.get(access_type.lower(), ('r', None))

def sanitize_name(name):
    """
    Limpia y formatea nombres para usar en RDL.
    Reemplaza espacios y caracteres especiales por guiones bajos.
    """
    return str(name).strip().replace(' ', '_').replace('-', '_')

def generate_rdl_from_excel(excel_file, output_file):
    """
    Genera un archivo SystemRDL completo desde un Excel con formato de especificación.
    
    Parámetros:
        excel_file: ruta al archivo Excel de entrada
        output_file: ruta donde se guardará el archivo .rdl generado
    """
    
    try:
        print(f"Leyendo archivo Excel: {excel_file}")
        
        # ============================================
        # PASO 1: Leer las tres hojas del Excel
        # ============================================
        
        # Hoja "Blocks": contiene los bloques principales
        df_blocks = pd.read_excel(excel_file, sheet_name='Blocks')
        df_blocks.columns = df_blocks.columns.str.strip()
        
        # Hoja "Registers": contiene los registros de cada bloque
        df_registers = pd.read_excel(excel_file, sheet_name='Registers')
        df_registers.columns = df_registers.columns.str.strip()
        
        # Hoja "Fields": contiene los campos de cada registro
        df_fields = pd.read_excel(excel_file, sheet_name='Fields')
        df_fields.columns = df_fields.columns.str.strip()
        
        print(f"✓ Bloques encontrados: {len(df_blocks)}")
        print(f"✓ Registros encontrados: {len(df_registers)}")
        print(f"✓ Fields encontrados: {len(df_fields)}")
        
        # ============================================
        # PASO 2: Crear estructuras de datos
        # ============================================
        
        # Crear mapeo de registros por bloque
        # Esto nos permite saber qué registros pertenecen a cada bloque
        registers_by_block = df_registers.groupby('Block Name')
        
        # Crear mapeo de fields por registro
        # Esto nos permite saber qué campos tiene cada registro
        fields_by_register = df_fields.groupby('Register Name')
        
        # ============================================
        # PASO 3: Comenzar a escribir el archivo RDL
        # ============================================
        
        with open(output_file, 'w', encoding='utf-8') as f:
            
            # Procesar cada bloque
            for block_idx, block in df_blocks.iterrows():
                block_name = sanitize_name(block['Block Name'])
                base_address = str(block['Base Address']).strip()
                block_desc = str(block['Description']).strip() if pd.notna(block['Description']) else f"{block_name} Block"
                
                print(f"\n📦 Procesando bloque: {block_name}")
                
                # Escribir encabezado del addrmap
                f.write(f"addrmap {block_name} {{\n")
                f.write(f"    name = \"{block_name}\";\n")
                f.write(f"    desc = \"{block_desc}\";\n\n")
                
                # ============================================
                # PASO 4: Procesar registros de este bloque
                # ============================================
                
                # Verificar si este bloque tiene registros
                if block_name not in registers_by_block.groups:
                    print(f"  ⚠ Advertencia: No se encontraron registros para el bloque {block_name}")
                    f.write(f"    // No se encontraron registros para este bloque\n\n")
                    f.write("};\n\n")
                    continue
                
                # Obtener todos los registros de este bloque
                block_registers = registers_by_block.get_group(block_name)
                
                for reg_idx, register in block_registers.iterrows():
                    reg_name = sanitize_name(register['Register Name'])
                    reg_offset = str(register['Offset']).strip()
                    reg_desc = str(register['Description']).strip() if pd.notna(register['Description']) else f"{reg_name} Register"
                    reg_width = int(register['Width (bits)']) if pd.notna(register['Width (bits)']) else 32
                    
                    print(f"  📝 Procesando registro: {reg_name} @ {reg_offset}")
                    
                    f.write(f"    // Registro {reg_name}\n")
                    f.write(f"    reg {{\n")
                    f.write(f"        name = \"{reg_name}\";\n")
                    f.write(f"        desc = \"{reg_desc}\";\n")
                    f.write(f"        regwidth = {reg_width};\n\n")
                    
                    # ============================================
                    # PASO 5: Procesar campos de este registro
                    # ============================================
                    
                    # Verificar si este registro tiene campos
                    if reg_name not in fields_by_register.groups:
                        print(f"    ⚠ Advertencia: No se encontraron campos para el registro {reg_name}")
                        f.write(f"        // No se encontraron campos para este registro\n\n")
                        f.write(f"    }} {reg_name} @ {reg_offset};\n\n")
                        continue
                    
                    # Obtener todos los campos de este registro
                    register_fields = fields_by_register.get_group(reg_name)
                    
                    # Ordenar campos por LSB para mejor legibilidad
                    register_fields = register_fields.sort_values('LSB')
                    
                    for field_idx, field in register_fields.iterrows():
                        field_name = sanitize_name(field['Field Name'])
                        lsb = int(field['LSB'])
                        width = int(field['Width'])
                        msb = lsb + width - 1
                        access = str(field['Access']).strip()
                        reset_value = int(field['Reset Value']) if pd.notna(field['Reset Value']) else 0
                        field_desc = str(field['Description']).strip() if pd.notna(field['Description']) else f"{field_name} field"
                        
                        # Convertir tipo de acceso a formato RDL
                        sw_access, onwrite = access_to_rdl(access)
                        
                        # Calcular el valor de reset en formato binario
                        reset_bin = format(reset_value, f'0{width}b')
                        
                        print(f"    - Campo: {field_name}[{msb}:{lsb}] = {width}'b{reset_bin} ({access})")
                        
                        # Escribir definición del campo
                        f.write(f"        field {{\n")
                        f.write(f"            name = \"{field_name}\";\n")
                        f.write(f"            desc = \"{field_desc}\";\n")
                        f.write(f"            sw = {sw_access};\n")
                        f.write(f"            hw = r;\n")
                        
                        # Agregar comportamiento especial si existe (como w1c)
                        if onwrite:
                            f.write(f"            onwrite = {onwrite};\n")
                        
                        f.write(f"        }} {field_name}[{msb}:{lsb}] = {width}'b{reset_bin};\n\n")
                    
                    # Cerrar definición del registro
                    f.write(f"    }} {reg_name} @ {reg_offset};\n\n")
                
                # Cerrar definición del addrmap
                f.write("};\n\n")
        
        print(f"\n✅ Archivo RDL generado exitosamente: {output_file}")
        print(f"\n📋 Siguientes pasos:")
        print(f"  1. Compilar: peakrdl regblock {output_file} -o output")
        print(f"  2. Generar HTML: peakrdl html {output_file} -o output_html")
        print(f"  3. Abrir: open output_html/index.html")
        
    except FileNotFoundError:
        print(f"❌ Error: No se pudo encontrar el archivo {excel_file}")
        print(f"   Verifica que el archivo existe y la ruta es correcta")
    except KeyError as e:
        print(f"❌ Error: No se encontró la columna o hoja esperada: {str(e)}")
        print(f"   Verifica que el Excel tenga las hojas 'Blocks', 'Registers' y 'Fields'")
        print(f"   con las columnas correctas")
    except Exception as e:
        print(f"❌ Error al procesar el archivo: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("  Conversor de Excel a SystemRDL")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\n📖 Uso: python excel_to_rdl.py <archivo_excel.xlsx> [archivo_salida.rdl]")
        print("\n📝 Ejemplo:")
        print("  python excel_to_rdl.py register_spec.xlsx output.rdl")
        print("\n📋 Formato del Excel requerido:")
        print("  - Hoja 'Blocks': Block Name, Base Address, Size, Description")
        print("  - Hoja 'Registers': Block Name, Register Name, Offset, Description, Width (bits)")
        print("  - Hoja 'Fields': Register Name, Field Name, LSB, Width, Access, Reset Value, Description")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "generated_registers.rdl"
    
    generate_rdl_from_excel(excel_file, output_file)
    
    print("\n" + "=" * 60)