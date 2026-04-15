import xml.etree.ElementTree as ET

def modify_drawio(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    W = 120
    H = 45
    
    # 基础起点
    START_X = 40
    START_Y = 80
    
    X_GAP = 30
    Y_GAP = 20
    
    def get_x(col):
        return START_X + col * (W + X_GAP)
        
    def get_y(row):
        return START_Y + row * (H + Y_GAP)
        
    layout = {}
    
    # Col 0 (Input & Master Agent) - Center aligned to Rows 2-5
    layout['act_in'] = (get_x(0), get_y(2))
    layout['dat_in'] = (get_x(0), get_y(3))
    layout['act_m'] = (get_x(0), get_y(4))
    layout['dat_m'] = (get_x(0), get_y(5))
    
    # Col 1 & 2 (Category Agents)
    # c1 aligns to s1,s2,s3 (Row 0,1,2 -> center Row 1)
    layout['act_c1'] = (get_x(1), get_y(1))
    layout['dat_c1'] = (get_x(2), get_y(1))
    
    # c2 aligns to s4,s5 (Row 3,4 -> center 3.5)
    c2_y = (get_y(3) + get_y(4)) / 2
    layout['act_c2'] = (get_x(1), c2_y)
    layout['dat_c2'] = (get_x(2), c2_y)
    
    # c3 aligns to s6 (Row 5)
    layout['act_c3'] = (get_x(1), get_y(5))
    layout['dat_c3'] = (get_x(2), get_y(5))
    
    # c4 aligns to s7 (Row 6)
    layout['act_c4'] = (get_x(1), get_y(6))
    layout['dat_c4'] = (get_x(2), get_y(6))
    
    # c5 aligns to s8 (Row 7)
    layout['act_c5'] = (get_x(1), get_y(7))
    layout['dat_c5'] = (get_x(2), get_y(7))
    
    # Col 3 & 4 (Skills)
    for i in range(8):
        layout[f'act_s{i+1}'] = (get_x(3), get_y(i))
        layout[f'dat_s{i+1}'] = (get_x(4), get_y(i))
        
    # Col 5 (Learning & Rules)
    layout['act_learn'] = (get_x(5), get_y(2))
    layout['dat_learn'] = (get_x(5), get_y(3))
    layout['act_eval'] = (get_x(5), get_y(4))
    layout['dat_rules'] = (get_x(5), get_y(5))
    
    # Online Section (Right side, Row 0 to 7)
    online_x = get_x(6) + 20 # margin
    for i, node in enumerate(['act_up', 'dat_doc', 'act_route', 'dat_cmd', 'act_load', 'dat_run', 'act_match', 'dat_res']):
        layout[node] = (online_x, get_y(i))
        
    # Boxes
    offline_w = get_x(5) + W + 20 - 20
    offline_h = get_y(7) + H + 20 - 40
    online_w = 160
    
    # Apply
    for cell in root.iter('mxCell'):
        cell_id = cell.get('id')
        if not cell_id: continue
        
        geo = cell.find('mxGeometry')
        if geo is not None:
            if cell_id in layout:
                geo.set('x', str(layout[cell_id][0]))
                geo.set('y', str(layout[cell_id][1]))
                geo.set('width', str(W))
                geo.set('height', str(H))
            elif cell_id == 'box_offline':
                geo.set('x', '20')
                geo.set('y', '40')
                geo.set('width', str(offline_w))
                geo.set('height', str(offline_h))
            elif cell_id == 'title_offline':
                geo.set('x', '20')
                geo.set('y', '50')
                geo.set('width', str(offline_w))
            elif cell_id == 'box_online':
                geo.set('x', str(online_x - 20))
                geo.set('y', '40')
                geo.set('width', str(online_w))
                geo.set('height', str(offline_h))
            elif cell_id == 'title_online':
                geo.set('x', str(online_x - 20))
                geo.set('y', '50')
                geo.set('width', str(online_w))
                
            # Clear array waypoints so Draw.io auto-routes orthogonal edges
            array = geo.find('Array')
            if array is not None:
                geo.remove(array)

    tree.write(file_path, encoding='utf-8', xml_declaration=False)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

modify_drawio('/mnt/e/pyProject/aiso/test_files/aiso_approach.drawio')
