import json
import ast
import pandas as pd
from django.shortcuts import render
from splitwise.settings import PRIVATE_KEY
from .models import User, UserProfile, Receipt
from django.core.files.storage import FileSystemStorage
from django.core.files import File
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from PIL import Image
from PIL.ImageOps import exif_transpose
from pytesseract import pytesseract
import numpy as np
import cv2
import os


# Create your views here.
def index(request):
    if request.method == 'GET':
        user_profiles = UserProfile.objects.all()
        return render(request, 'web/index.html', context={'user_profiles': user_profiles})

    elif request.method == 'POST':
        receipt_title = request.POST.get('receipt_title')
        receipt_contributors_ids = request.POST.getlist('receipt_contributors')

        receipt_image = request.FILES['receipt_image']

        fs = FileSystemStorage()

        fs.save(f'media/Receipts/{receipt_title}/raw/{receipt_image.name}', receipt_image)

        # receipt_image_converted = cv2.imread(receipt_image)

        # if receipt_image_converted.size[0] < receipt_image_converted.size[1]:
        #     resize_factor = round(1000 / receipt_image_converted.size[1], 2)
        # else:
        #     resize_factor = round(1000 / receipt_image_converted.size[0], 2)
        #
        # new_size = (
        # int(resize_factor * receipt_image_converted.size[0]), int(resize_factor * receipt_image_converted.size[1]))
        #
        # resized_receipt_img = exif_transpose(receipt_image_converted.resize(new_size))

        # resized_receipt_img.save(f'{fs.base_location}media/Receipts/{receipt_title}/raw/converted-{receipt_image.name}')

        # receipt_image_converted.save(f'{fs.base_location}media/Receipts/{receipt_title}/raw/converted-{receipt_image.name}')

        converted_receipt_url = f'{fs.base_location}media/Receipts/{receipt_title}/raw/{receipt_image.name}'

        receipt_contributors = UserProfile.objects.filter(pk__in=receipt_contributors_ids)

        receipt = Receipt(title=receipt_title, raw_image_url=converted_receipt_url)
        receipt.save()

        for contributor in receipt_contributors:
            receipt.contributors.add(contributor)
        receipt.save()

        user_profiles = UserProfile.objects.all()

        return render(request, 'web/index.html', context={'result': 200, 'receipt': receipt,
                                                          'user_profiles': user_profiles})


def render_receipt(request, receipt_pk, confidence_rate=70):
    if Receipt.objects.filter(pk=receipt_pk):
        target_receipt = Receipt.objects.filter(pk=receipt_pk)[0]

        coordination, coordination_dict = process_receipt(target_receipt, confidence_rate)

        coordination_json = json.dumps(coordination)

        return render(request, 'web/receipt.html', context={'receipt': target_receipt,
                                                            'confidence_rate': confidence_rate,
                                                            'coordination': coordination_json,
                                                            'coordination_dict': coordination_dict})

    else:
        return render(request, 'web/404.html', context={'receipt_pk': receipt_pk})


def process_receipt(receipt, confidence_threshold=70):
    rectangles_coordination = {}
    rectangles_coordination_dict = {}
    fs = FileSystemStorage()

    # raw_receipt = np.array(Image.open(f"{receipt.raw_image_url}"))
    raw_receipt = cv2.imread(f"{receipt.raw_image_url}")
    # raw_receipt = cv2.imread(f"/home/farzam/Desktop/Samples/today.jpg")

    gray = cv2.cvtColor(raw_receipt, cv2.COLOR_BGR2GRAY)

    # denoise = cv2.medianBlur(gray, 5)

    # canny = cv2.Canny(gray, 200, 80)

    results = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, lang='eng', config='--psm 6')

    for i in range(0, len(results["text"])):

        x = results["left"][i]
        y = results["top"][i]
        w = results["width"][i]
        h = results["height"][i]

        text = results["text"][i]
        conf = int(results["conf"][i])

        if conf > confidence_threshold:
            if len(text.strip()) > 0:
                if conf > confidence_threshold:
                    rectangles_coordination[str(i) + '|' + text] = [x, y, w, h]
                    rectangles_coordination_dict[i, text] = [x, y, x + w, y + h]

    if not os.path.exists(f'{fs.base_location}media/Receipts/{receipt.title}/processed/'):
        os.mkdir(f'{fs.base_location}media/Receipts/{receipt.title}/processed/')

    cv2.imwrite(f'{fs.base_location}media/Receipts/{receipt.title}/processed/processed.jpg', raw_receipt)

    receipt.processed_image_url = f'/media/Receipts/{receipt.title}/processed/processed.jpg'
    receipt.save()

    return rectangles_coordination, rectangles_coordination_dict


@csrf_exempt
def process_submitted_data(request, receipt_pk):
    if request.method == "POST":
        cost_items = ast.literal_eval(request.POST.get('data'))['filtered_rectangles']
        payer_pk = request.POST.get('payer')

        payer = UserProfile.objects.filter(pk=payer_pk)[0]

        receipt = Receipt.objects.filter(pk=receipt_pk)[0]

        columns = ['id', 'price', 'payer']

        for contributor in receipt.contributors.all():
            columns.append(contributor.user.username)

        df = pd.DataFrame(columns=columns)

        for idx, item in enumerate(cost_items):
            item_contributors_pk = item['contributors'].split(',')
            item_contributors = UserProfile.objects.filter(pk__in=item_contributors_pk).all()
            item_id = str(item['id'].split('|')[0])
            item_price = str(item['id'].split('|')[1])

            if ',' in item_price:
                item_price = item_price.replace(',', '.')

            required_empty_slots = len(receipt.contributors.all())

            row = [item_id, item_price, payer.user.username]

            for i in range(required_empty_slots):
                row.append(0)

            df.loc[idx] = row

            for contributor in item_contributors.all():
                df[contributor.user.username].iloc[idx] = round(float(item_price) / len(item_contributors.all()), 2)

        sum_columns = df.columns[3:]
        df.loc['Total'] = df[sum_columns].sum()

        df.loc['Total', 'id'] = ''
        df.loc['Total', 'price'] = ''
        df.loc['Total', 'payer'] = payer

        fs = FileSystemStorage()

        csv_data_directory = f'{fs.base_location}/media/Receipts/{receipt.title}/csv/'

        if not os.path.exists(csv_data_directory):
            os.mkdir(csv_data_directory)

        csv_data_url = f'/media/Receipts/{receipt.title}/csv/data.csv'

        df.to_csv(os.path.join(csv_data_directory, 'data.csv'))

        return JsonResponse(data={'df': df.to_html(),
                                  'csv_data_url': csv_data_url})


@csrf_exempt
def check_user_private_key(request):
    if request.method == "POST":
        entered_private_key = request.POST.get('private_key')

        if entered_private_key == PRIVATE_KEY:
            status = 200
        else:
            status = 201

        return JsonResponse(data={'private_key_status': status})
