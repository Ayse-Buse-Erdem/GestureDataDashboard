import cv2

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Kamera açılamadı.")
    raise SystemExit

print("Kamera açıldı. Kapatmak için Q tuşuna bas.")

while True:
    success, frame = camera.read()

    if not success:
        print("Görüntü alınamadı.")
        break

    cv2.imshow("Gesture Data Dashboard - Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()