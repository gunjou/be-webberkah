import face_recognition


def verifikasi_wajah(id_karyawan, image):
    # get file and filename
    file_path = f"./{id_karyawan}.png"
    # file_name = os.path.splitext(os.path.basename(file_path))[0]

    # Load image
    known_image = face_recognition.load_image_file(file_path)
    unknown_image = face_recognition.load_image_file(image)
    # Image embedding
    known_encoding = face_recognition.face_encodings(known_image)[0]
    unknown_encoding = face_recognition.face_encodings(unknown_image)[0]

    # Compare image
    results = face_recognition.compare_faces([known_encoding], unknown_encoding)

    return results[0]