import openpyxl
from openpyxl.utils import get_column_letter

# Define filename 
filename = 'output.xlsx'

# Load workbook
workbook = openpyxl.load_workbook('output.xlsx')

# Loop all sheets in workbook
for sheet in workbook:
    # Loop all columns in  sheet
    for col in sheet.columns:
        # Get maximum length of any cell in the column
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        # Set width of column to maximum length of any cell
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width

# Save the modified workbook
workbook.save('output.xlsx')
