from dataclasses import dataclass
from os import listdir
from os.path import  isfile, join, basename
from typing import List
import sys
from lxml import etree

@dataclass
class BoundingBox:
    """
    Bounding box data class for XML bounding box manipulation
    """
    x_min: int = 0
    x_max: int = 0
    y_min: int = 0
    y_max: int = 0


class BoxResizer:
    """
    Resize XML boxes by a scale factor for all XMLS in a directory
    Positive scale factors increase the box size by scale_factor percent, negative scale_factors reduce box size.
    Boxes will trim to stay inside the total width allowed for the image the XML file is based on. 
    Boxes too large once scaled will meet the boarder of the image, but will not continue out of bounds.
    """
    def __init__(self, input_directory: str, output_directory: str, scale_factor: float) -> None:
        """
        Set up the directory we're reading from and the file list as empty
        """
        # The XML tags for our labeling software conventions:
        self.XML_object_tag = "object"
        self.bounding_box_tag = "bndbox"
        self.base_image_size_tag = "size"
        self.base_image_width_tag = "width"
        self.base_image_height_tag = "height"
        self.x_min_tag = "xmin"
        self.x_max_tag = "xmax"
        self.y_min_tag = "ymin"
        self.y_max_tag = "ymax"
        # size of an entire XML frame. (total size of the image to limit our boxes to in-bounds only)
        self.width = 0
        self.height = 0
        # Directory with input XMLs
        self.input_directory = input_directory
        # Directory to store XMLs (if same as input will overwrite)
        self.output_directory = output_directory
        # If scale factor is positive will always scale up, if negative will always scale down.
        self.scale_factor = scale_factor
        
        self.xml_files = []

    def get_scaled_box(self, box: BoundingBox) -> BoundingBox:
        """
        Get a new box rescaled to the scale factor.
        """    
        x_length = (box.x_max - box.x_min)/2
        y_length = (box.y_max - box.y_min)/2

        box.x_min -= int(x_length*self.scale_factor)
        box.x_max += int(x_length*self.scale_factor) 
        box.y_min -= int(y_length*self.scale_factor)
        box.y_max += int(y_length*self.scale_factor) 

        box.x_max = min(self.width, box.x_max)
        box.x_min = max(0, box.x_min)
        box.y_max = min(self.height, box.y_max)
        box.y_min = max(0, box.y_min)
        return box



    def get_XML_files(self) -> List[str]:
        """
        Get all XML files in a given directory path
        """
        # Files with sub dirs, etc.. Need to filter
        dir_contents: List[str] = listdir(self.input_directory)

        # Get only files, and only those with XML extension. Append the directory path also.
        self.xml_files = [file for file in dir_contents if (isfile(join(self.input_directory, file)) and file.endswith(".xml"))]
        self.xml_files = [join(self.input_directory, file) for file in self.xml_files]

    def XML_to_BoundingBox(self, XMLObject) -> BoundingBox:
        """
        Given an XML bounding box object, extract the corners of the box as a BoundingBox
        """
        current_bounding_box = BoundingBox()
        for coordinate in XMLObject:
            if coordinate.tag == self.x_min_tag:
                current_bounding_box.x_min = int(coordinate.text)
            elif coordinate.tag == self.x_max_tag:
                current_bounding_box.x_max = int(coordinate.text)
            elif coordinate.tag == self.y_min_tag:
                current_bounding_box.y_min = int(coordinate.text)
            elif coordinate.tag == self.y_max_tag:
                current_bounding_box.y_max = int(coordinate.text)
        return 
        
    def XML_to_BoundingBox(self, XMLObject) -> BoundingBox:
        """
        Given an XML bounding box object, extract the corners of the box as a BoundingBox
        """
        box = BoundingBox()
        for coordinate in XMLObject:
            if coordinate.tag == self.x_min_tag:
                box.x_min = int(coordinate.text)
            elif coordinate.tag == self.x_max_tag:
                box.x_max = int(coordinate.text)
            elif coordinate.tag == self.y_min_tag:
                box.y_min = int(coordinate.text)
            elif coordinate.tag == self.y_max_tag:
                box.y_max = int(coordinate.text)
        return box

    def write_BoundingBox_to_XML(self, box: BoundingBox, XMLObject) -> None:
        
        for coordinate in XMLObject:
            if coordinate.tag == self.x_min_tag:
                coordinate.text = str(box.x_min)
            elif coordinate.tag == self.x_max_tag:
                coordinate.text = str(box.x_max)
            elif coordinate.tag == self.y_min_tag:
                coordinate.text = str(box.y_min)
            elif coordinate.tag == self.y_max_tag:
                coordinate.text = str(box.y_max)

    def scale_XML_files(self) -> None:
        """
        Return all XML data as a list of XML data trees
        """
        self.get_XML_files()

        for file in self.xml_files:
            XML_file_tree = etree.parse(file)
            
            # Get base image size to limit boxes to in-bounds.
            XML_image_size = XML_file_tree.find(self.base_image_size_tag)
            self.width = int(XML_image_size.find(self.base_image_width_tag).text)
            self.height = int(XML_image_size.find(self.base_image_height_tag).text)

            # Get all bounding box objects of the form: 
            # object : {name, pose, truncated, difficult, 
            # bndbox : {xmin, ymin, xmax, ymax} }
            box_XML_objects = XML_file_tree.findall(self.XML_object_tag)

            
            for box_XML_object in box_XML_objects:
                # Get just the coordinate sub object of the form:  
                # bndbox : {xmin, ymin, xmax, ymax}
                current_box_XML = box_XML_object.find(self.bounding_box_tag)

                # Convert to BoundingBox type
                current_box = self.XML_to_BoundingBox(current_box_XML)
                scaled_box = self.get_scaled_box(current_box)
             
                self.write_BoundingBox_to_XML(scaled_box, current_box_XML)
            
                   

            # Write each XML to a file in the output directory
            print("writing output to: ", join(self.output_directory,basename(file)))
            XML_file_tree.write(join(self.output_directory,basename(file)))


def help() -> None:
    print("Use the form:")
    print("python3 resize_boxes.py input_dir output_dir scale_factor")
    print("Example, to reduce each box by a scale factor of -.5 use:")
    print("python3 resize_boxes.py /mnt/c/Users/zhill/labeling_utils ./outputxml -.5")
    print("Positive scale factors increase box size, negative factors decrease size.")

if __name__ == "__main__":

    if "--help" in sys.argv:
        help()
        exit()

    if len(sys.argv) != 4:
        print("Bad arguments")
        help()
        exit()

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    scale_factor = float(sys.argv[3])

    XMLScaler = BoxResizer(input_dir, output_dir, scale_factor)
    XMLScaler.scale_XML_files()