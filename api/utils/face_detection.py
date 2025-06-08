import face_recognition


def verifikasi_wajah(id_karyawan, image):
    try:
        file_path = f"./cropped_faces/{id_karyawan}.jpg"

        known_image = face_recognition.load_image_file(file_path)
        unknown_image = face_recognition.load_image_file(image)

        known_encodings = face_recognition.face_encodings(known_image)
        unknown_encodings = face_recognition.face_encodings(unknown_image)

        if len(known_encodings) == 0 or len(unknown_encodings) == 0:
            return "not_detected"

        known_encoding = known_encodings[0]
        unknown_encoding = unknown_encodings[0]

        results = face_recognition.compare_faces([known_encoding], unknown_encoding)

        return results[0]
    
    except Exception as e:
        print(f"[ERROR verifikasi_wajah] {e}")
        return "error"
