import xml.etree.ElementTree as ET
import re

def modify_drawio(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Define styles
    # Action (was parallelogram, now rectangle)
    action_style = "shape=rectangle;rounded=0;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;fontStyle=1;fontSize=12;align=center;verticalAlign=middle;"
    # Data (was rectangle, now parallelogram)
    data_style = "shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fixedSize=1;fillColor=#D5E8D4;strokeColor=#82B366;fontStyle=1;fontSize=12;align=center;verticalAlign=middle;"
    
    # Layout constants
    W = 120
    H = 45
    Y_GAP = 20
    X_GAP = 20
    
    # Calculate grid Y
    def get_y(row):
        return 60 + row * (H + Y_GAP)
        
    # Calculate grid X for skills (8 slots)
    S_X = [40 + i * (W + X_GAP) for i in range(8)]
    
    # Map elements to their new positions
    layout = {
        # Offline - Center (Slot 3.5) -> (S_X[3] + S_X[4]) / 2
        'act_in': ( (S_X[3]+S_X[4])/2, get_y(0) ),
        'dat_in': ( (S_X[3]+S_X[4])/2, get_y(1) ),
        'act_m': ( (S_X[3]+S_X[4])/2, get_y(2) ),
        'dat_m': ( (S_X[3]+S_X[4])/2, get_y(3) ),
        
        # Categories (Row 4, 5)
        'act_c1': ( S_X[1], get_y(4) ), # Center of 0,1,2
        'dat_c1': ( S_X[1], get_y(5) ),
        'act_c2': ( (S_X[3]+S_X[4])/2, get_y(4) ), # Center of 3,4
        'dat_c2': ( (S_X[3]+S_X[4])/2, get_y(5) ),
        'act_c3': ( S_X[5], get_y(4) ),
        'dat_c3': ( S_X[5], get_y(5) ),
        'act_c4': ( S_X[6], get_y(4) ),
        'dat_c4': ( S_X[6], get_y(5) ),
        'act_c5': ( S_X[7], get_y(4) ),
        'dat_c5': ( S_X[7], get_y(5) ),
        
        # Skills (Row 6, 7)
        'act_s1': ( S_X[0], get_y(6) ), 'dat_s1': ( S_X[0], get_y(7) ),
        'act_s2': ( S_X[1], get_y(6) ), 'dat_s2': ( S_X[1], get_y(7) ),
        'act_s3': ( S_X[2], get_y(6) ), 'dat_s3': ( S_X[2], get_y(7) ),
        'act_s4': ( S_X[3], get_y(6) ), 'dat_s4': ( S_X[3], get_y(7) ),
        'act_s5': ( S_X[4], get_y(6) ), 'dat_s5': ( S_X[4], get_y(7) ),
        'act_s6': ( S_X[5], get_y(6) ), 'dat_s6': ( S_X[5], get_y(7) ),
        'act_s7': ( S_X[6], get_y(6) ), 'dat_s7': ( S_X[6], get_y(7) ),
        'act_s8': ( S_X[7], get_y(6) ), 'dat_s8': ( S_X[7], get_y(7) ),
        
        # Learning (Row 8, 9, 10, 11)
        'act_learn': ( (S_X[3]+S_X[4])/2, get_y(8) ),
        'dat_learn': ( (S_X[3]+S_X[4])/2, get_y(9) ),
        'act_eval': ( (S_X[3]+S_X[4])/2, get_y(10) ),
        'dat_rules': ( (S_X[3]+S_X[4])/2, get_y(11) ),
    }
    
    # Offline Box
    offline_w = S_X[7] + W + 20 - 20
    offline_h = get_y(11) + H + 20 - 40
    
    # Online Box
    online_x = 20 + offline_w + 40
    online_w = 240
    online_center_x = online_x + (online_w - W) / 2
    
    # Online nodes
    online_rows = [2, 3, 4, 5, 6, 7, 8, 9]
    online_ids = ['act_up', 'dat_doc', 'act_route', 'dat_cmd', 'act_load', 'dat_run', 'act_match', 'dat_res']
    for i, oid in enumerate(online_ids):
        layout[oid] = (online_center_x, get_y(online_rows[i]))
        
    # Apply changes
    for cell in root.iter('mxCell'):
        cell_id = cell.get('id')
        if not cell_id:
            continue
            
        # 1. Swap styles
        if cell_id.startswith('act_'):
            cell.set('style', action_style)
        elif cell_id.startswith('dat_'):
            cell.set('style', data_style)
            
        # 2. Update geometry
        geo = cell.find('mxGeometry')
        if geo is not None:
            # Update width/height for all nodes
            if cell_id.startswith('act_') or cell_id.startswith('dat_'):
                geo.set('width', str(W))
                geo.set('height', str(H))
                
            # Update positions
            if cell_id in layout:
                geo.set('x', str(layout[cell_id][0]))
                geo.set('y', str(layout[cell_id][1]))
                
            # Update boxes
            elif cell_id == 'box_offline':
                geo.set('width', str(offline_w))
                geo.set('height', str(offline_h))
            elif cell_id == 'title_offline':
                geo.set('width', str(offline_w))
            elif cell_id == 'box_online':
                geo.set('x', str(online_x))
                geo.set('width', str(online_w))
                geo.set('height', str(offline_h))
            elif cell_id == 'title_online':
                geo.set('x', str(online_x))
                geo.set('width', str(online_w))
                
            # Update edge waypoints (Array points)
            array = geo.find('Array')
            if array is not None:
                # We need to recalculate waypoints for edges
                # e_d_c1_s1: dat_c1 -> act_s1
                if cell_id == 'e_d_c1_s1':
                    points = array.findall('mxPoint')
                    if len(points) == 2:
                        points[0].set('x', str(layout['dat_c1'][0] + W/2))
                        points[0].set('y', str(layout['dat_c1'][1] + H + Y_GAP/2))
                        points[1].set('x', str(layout['act_s1'][0] + W/2))
                        points[1].set('y', str(layout['dat_c1'][1] + H + Y_GAP/2))
                elif cell_id == 'e_d_c1_s3':
                    points = array.findall('mxPoint')
                    if len(points) == 2:
                        points[0].set('x', str(layout['dat_c1'][0] + W/2))
                        points[0].set('y', str(layout['dat_c1'][1] + H + Y_GAP/2))
                        points[1].set('x', str(layout['act_s3'][0] + W/2))
                        points[1].set('y', str(layout['dat_c1'][1] + H + Y_GAP/2))
                elif cell_id == 'e_d_c2_s5':
                    points = array.findall('mxPoint')
                    if len(points) == 2:
                        points[0].set('x', str(layout['dat_c2'][0] + W/2))
                        points[0].set('y', str(layout['dat_c2'][1] + H + Y_GAP/2))
                        points[1].set('x', str(layout['act_s5'][0] + W/2))
                        points[1].set('y', str(layout['dat_c2'][1] + H + Y_GAP/2))
                # Edges to learning
                elif cell_id in ['e_d_s1_l', 'e_d_s2_l', 'e_d_s3_l', 'e_d_s4_l', 'e_d_s7_l', 'e_d_s8_l']:
                    points = array.findall('mxPoint')
                    src_id = cell_id.replace('e_d_', 'dat_').replace('_l', '')
                    if len(points) == 2:
                        points[0].set('x', str(layout[src_id][0] + W/2))
                        points[0].set('y', str(layout['dat_s1'][1] + H + Y_GAP/2))
                        points[1].set('x', str(layout['act_learn'][0] + W/2))
                        points[1].set('y', str(layout['dat_s1'][1] + H + Y_GAP/2))
                # Cross edge
                elif cell_id == 'e_cross':
                    points = array.findall('mxPoint')
                    if len(points) == 2:
                        points[0].set('x', str(online_x - 30))
                        points[0].set('y', str(layout['dat_rules'][1] + H/2))
                        points[1].set('x', str(online_x - 30))
                        points[1].set('y', str(layout['act_load'][1] + H/2))

    tree.write(file_path, encoding='utf-8', xml_declaration=False)
    
    # Fix the missing XML declaration manually
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

modify_drawio('/mnt/e/pyProject/aiso/test_files/aiso_approach.drawio')
