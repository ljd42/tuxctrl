import math 

def rotate_z(point, angle):
    """Rotate 3D point around Z-axis"""
    x, y, z = point
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (x * cos_a + y * sin_a, -x * sin_a + y * cos_a, z)
      
def rotate_y(point, angle):
    """Rotate 3D point around Y-axis"""
    x, y, z = point
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (x * cos_a + z * sin_a, y, -x * sin_a + z * cos_a)

def rotate_x(point, angle):
    """Rotate 3D point around X-axis"""
    x, y, z = point
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (x, y * cos_a - z * sin_a, y * sin_a + z * cos_a)

def translate(point, v): 
    x, y, z = point
    vx, vy, vz = v
    return (x+vx, y+vy, z+vz)

def project_3d_to_2d(point, width, height, distance=5):
    """Simple perspective projection"""
    x, y, z = point
    factor = distance / (distance + z + 3)  # Avoid division by zero
    proj_x = x * factor * width//2 + width // 2
    proj_y = -y * factor * width//2 + height // 2
    return (int(proj_x), int(proj_y))
