# Receipt OCR using pytesseract hosted on Django
This is a Django project, which aims to provide a simple front-end for users to upload their receipts photo and get them annotated by pytesseract library.

## Requirements
To install the deendencies, simply run `pip install -r requirements.txt`

## Run
Since it's a Django application, you just need to `python manage.py runserver` and then visit `http://localhost:8000` to visit the `index.html` page and upload your first receipt image.

## Note
Since there is a file size limit in the `js` codes, you can modigy it later in the `index.html` file.
`Private Key` is a key to make sure only authenticated users can upload receipts.
