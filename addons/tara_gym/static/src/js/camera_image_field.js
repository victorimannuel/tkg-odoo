/** @odoo-module */

import { registry } from "@web/core/registry";
import { ImageField, imageField } from "@web/views/fields/image/image_field";
import { useRef, useState } from "@odoo/owl";

export class CameraImageField extends ImageField {
    static template = "tara_gym.CameraImageField";

    setup() {
        super.setup();
        this.cameraState = useState({ active: false });
        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
        this.stream = null;
    }

    async onCameraOpen() {
        this.cameraState.active = true;
        // Wait for DOM to render the video element
        await new Promise((resolve) => setTimeout(resolve, 100));
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
            });
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                this.videoRef.el.play();
            }
        } catch (err) {
            console.error("Camera access denied:", err);
            this.cameraState.active = false;
        }
    }

    onCameraCapture() {
        const video = this.videoRef.el;
        const canvas = this.canvasRef.el;
        if (!video || !canvas) return;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);

        const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
        const base64Data = dataUrl.split(",")[1];

        this.onCameraClose();
        this.props.record.update({ [this.props.name]: base64Data });
    }

    onCameraClose() {
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }
        this.cameraState.active = false;
    }
}

export const cameraImageField = {
    ...imageField,
    component: CameraImageField,
};

registry.category("fields").add("camera_image", cameraImageField);
