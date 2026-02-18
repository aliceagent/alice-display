/**
 * Touch Gesture Manager for Alice Display
 * Handles swipe, pinch, double-tap, and long press gestures
 */

class TouchGestureManager {
    constructor(aliceDisplay) {
        this.display = aliceDisplay;
        this.element = document.querySelector('.display-container');
        
        // Touch tracking state
        this.touches = new Map();
        this.isGesturing = false;
        this.lastTap = 0;
        this.longPressTimer = null;
        this.currentScale = 1;
        this.currentTranslateX = 0;
        this.currentTranslateY = 0;
        this.isZoomed = false;
        
        // Gesture thresholds
        this.SWIPE_THRESHOLD = 50;      // Minimum distance for swipe
        this.SWIPE_VELOCITY = 0.3;      // Minimum velocity for swipe
        this.DOUBLE_TAP_TIME = 300;     // Max time between taps for double-tap
        this.LONG_PRESS_TIME = 500;     // Duration for long press
        this.PINCH_THRESHOLD = 10;      // Minimum distance change for pinch
        this.MIN_SCALE = 1;             // Minimum zoom level
        this.MAX_SCALE = 4;             // Maximum zoom level
        
        this.init();
    }
    
    init() {
        // Bind touch event listeners
        this.element.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        this.element.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        this.element.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
        this.element.addEventListener('touchcancel', this.handleTouchCancel.bind(this), { passive: false });
        
        console.log('🤏 Touch gesture manager initialized');
    }
    
    handleTouchStart(e) {
        // Store touch points
        for (let touch of e.touches) {
            this.touches.set(touch.identifier, {
                id: touch.identifier,
                startX: touch.clientX,
                startY: touch.clientY,
                currentX: touch.clientX,
                currentY: touch.clientY,
                startTime: Date.now()
            });
        }
        
        const touchCount = e.touches.length;
        
        if (touchCount === 1) {
            this.handleSingleTouch(e);
        } else if (touchCount === 2) {
            this.handleTwoFingersStart(e);
        }
        
        // Prevent default behavior for gesture events
        if (touchCount > 1 || this.isZoomed) {
            e.preventDefault();
        }
    }
    
    handleSingleTouch(e) {
        const now = Date.now();
        const touch = Array.from(this.touches.values())[0];
        
        // Check for double-tap
        if (now - this.lastTap < this.DOUBLE_TAP_TIME) {
            this.handleDoubleTap(touch);
            this.lastTap = 0; // Reset to prevent triple-tap
            return;
        }
        
        this.lastTap = now;
        
        // Start long press timer
        this.longPressTimer = setTimeout(() => {
            this.handleLongPress(touch);
        }, this.LONG_PRESS_TIME);
    }
    
    handleTwoFingersStart(e) {
        // Clear single-touch timers
        this.clearLongPressTimer();
        
        // Store initial pinch state
        const touches = Array.from(this.touches.values());
        if (touches.length >= 2) {
            this.initialDistance = this.getDistance(touches[0], touches[1]);
            this.initialScale = this.currentScale;
            this.isGesturing = true;
            
            // Start two-finger long press timer for fullscreen
            this.twoFingerLongPressTimer = setTimeout(() => {
                this.handleTwoFingerLongPress();
                this.twoFingerLongPressTimer = null;
            }, this.LONG_PRESS_TIME);
        }
    }
    
    handleTouchMove(e) {
        // Update touch positions
        for (let touch of e.touches) {
            if (this.touches.has(touch.identifier)) {
                const stored = this.touches.get(touch.identifier);
                stored.currentX = touch.clientX;
                stored.currentY = touch.clientY;
            }
        }
        
        const touchCount = e.touches.length;
        
        if (touchCount === 1) {
            this.handleSingleTouchMove(e);
        } else if (touchCount === 2) {
            this.handlePinchMove(e);
        }
        
        // Prevent scrolling during gestures
        if (this.isGesturing || this.isZoomed || touchCount > 1) {
            e.preventDefault();
        }
    }
    
    handleSingleTouchMove(e) {
        // Clear long press if moving too much
        const touch = Array.from(this.touches.values())[0];
        const moveDistance = Math.sqrt(
            Math.pow(touch.currentX - touch.startX, 2) +
            Math.pow(touch.currentY - touch.startY, 2)
        );
        
        if (moveDistance > 10) {
            this.clearLongPressTimer();
        }
        
        // Handle panning when zoomed
        if (this.isZoomed) {
            const deltaX = touch.currentX - touch.startX;
            const deltaY = touch.currentY - touch.startY;
            this.updateImageTransform(this.currentScale, 
                this.currentTranslateX + deltaX, 
                this.currentTranslateY + deltaY);
            e.preventDefault();
        }
    }
    
    handlePinchMove(e) {
        const touches = Array.from(this.touches.values());
        if (touches.length < 2) return;
        
        // Clear two-finger long press timer since user is actively pinching
        if (this.twoFingerLongPressTimer) {
            clearTimeout(this.twoFingerLongPressTimer);
            this.twoFingerLongPressTimer = null;
        }
        
        const currentDistance = this.getDistance(touches[0], touches[1]);
        const scale = (currentDistance / this.initialDistance) * this.initialScale;
        
        // Apply scale limits
        const constrainedScale = Math.max(this.MIN_SCALE, Math.min(this.MAX_SCALE, scale));
        
        // Update image transform
        this.updateImageTransform(constrainedScale, this.currentTranslateX, this.currentTranslateY);
        
        e.preventDefault();
    }
    
    handleTouchEnd(e) {
        const touchCount = e.touches.length;
        
        // Store ended touch data before removing for swipe detection
        const endedTouches = [];
        for (let touch of e.changedTouches) {
            if (this.touches.has(touch.identifier)) {
                endedTouches.push(this.touches.get(touch.identifier));
            }
        }
        
        // Remove ended touches
        for (let touch of e.changedTouches) {
            this.touches.delete(touch.identifier);
        }
        
        // Clear timers
        this.clearLongPressTimer();
        
        // Handle end of gestures
        if (touchCount === 0) {
            this.handleGestureEnd(endedTouches);
        }
    }
    
    handleTouchCancel(e) {
        this.touches.clear();
        this.clearLongPressTimer();
        this.isGesturing = false;
    }
    
    handleGestureEnd(endedTouches = []) {
        // Check for swipe gesture if we had exactly one touch and weren't pinch gesturing
        if (endedTouches.length === 1 && !this.isGesturing) {
            this.checkForSwipe(endedTouches[0]);
        }
        
        this.isGesturing = false;
    }
    
    checkForSwipe(touch) {
        if (!touch) return;
        
        const deltaX = touch.currentX - touch.startX;
        const deltaY = touch.currentY - touch.startY;
        const deltaTime = Date.now() - touch.startTime;
        
        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        const velocity = distance / deltaTime;
        
        // Check if it's a horizontal swipe
        if (Math.abs(deltaX) > Math.abs(deltaY) && 
            Math.abs(deltaX) > this.SWIPE_THRESHOLD && 
            velocity > this.SWIPE_VELOCITY) {
            
            if (deltaX > 0) {
                this.handleSwipeRight();
            } else {
                this.handleSwipeLeft();
            }
        }
    }
    
    handleSwipeLeft() {
        console.log('👈 Swipe left detected - changing image');
        this.display.showToast('👈 Swipe: Changing image...');
        
        // Use existing change image functionality
        try {
            if (this.display && typeof this.display.handleChangeImage === 'function') {
                this.display.handleChangeImage();
            } else {
                console.warn('handleChangeImage not available');
            }
        } catch (error) {
            console.error('Error handling swipe left:', error);
            this.display.showToast('❌ Image change failed');
        }
    }
    
    handleSwipeRight() {
        console.log('👉 Swipe right detected - changing image');
        this.display.showToast('👉 Swipe: Changing image...');
        
        // Use existing change image functionality  
        try {
            if (this.display && typeof this.display.handleChangeImage === 'function') {
                this.display.handleChangeImage();
            } else {
                console.warn('handleChangeImage not available');
            }
        } catch (error) {
            console.error('Error handling swipe right:', error);
            this.display.showToast('❌ Image change failed');
        }
    }
    
    handleDoubleTap(touch) {
        console.log('👆👆 Double tap detected');
        
        try {
            if (this.isZoomed) {
                // Reset to original size
                this.resetZoom();
                this.display.showToast('🔍 Zoom reset');
            } else {
                // Zoom to 2x at tap location
                const zoomLevel = 2;
                const rect = this.element.getBoundingClientRect();
                const centerX = (touch.currentX - rect.left - rect.width / 2);
                const centerY = (touch.currentY - rect.top - rect.height / 2);
                
                this.updateImageTransform(zoomLevel, -centerX * 0.5, -centerY * 0.5);
                this.display.showToast('🔍 Zoomed 2x');
            }
        } catch (error) {
            console.error('Error handling double tap:', error);
            this.display.showToast('❌ Zoom failed');
        }
    }
    
    handleTwoFingerLongPress() {
        console.log('👆👆⏰ Two finger long press detected - toggling fullscreen');
        
        try {
            if (this.display && typeof this.display.toggleFullscreen === 'function') {
                this.display.toggleFullscreen();
                this.display.showToast('🖥️ Fullscreen toggled');
            } else {
                console.warn('toggleFullscreen not available');
            }
        } catch (error) {
            console.error('Error handling fullscreen gesture:', error);
            this.display.showToast('❌ Fullscreen failed');
        }
    }
    
    handleLongPress(touch) {
        console.log('👆⏰ Long press detected');
        this.display.showToast('⚡ Opening controls...');
        
        try {
            // Show image control panel
            if (this.display && typeof this.display.showImageControlPanel === 'function') {
                this.display.showImageControlPanel();
            } else {
                console.warn('showImageControlPanel not available');
            }
        } catch (error) {
            console.error('Error handling long press:', error);
            this.display.showToast('❌ Controls failed');
        }
    }
    
    updateImageTransform(scale, translateX, translateY) {
        this.currentScale = scale;
        this.currentTranslateX = translateX;
        this.currentTranslateY = translateY;
        this.isZoomed = scale > 1;
        
        // Apply transform to current image
        const activeImg = this.getActiveImage();
        if (activeImg) {
            activeImg.style.transform = `scale(${scale}) translate(${translateX}px, ${translateY}px)`;
            activeImg.style.transformOrigin = 'center center';
        }
    }
    
    resetZoom() {
        this.updateImageTransform(1, 0, 0);
        
        // Animate back to original state
        const activeImg = this.getActiveImage();
        if (activeImg) {
            activeImg.style.transition = 'transform 0.3s ease-out';
            setTimeout(() => {
                activeImg.style.transition = '';
            }, 300);
        }
    }
    
    getActiveImage() {
        // Get the currently visible image element
        const activeLayer = this.display.activeLayer;
        if (activeLayer === 'a') {
            return document.querySelector('#layer-a img');
        } else {
            return document.querySelector('#layer-b img');
        }
    }
    
    getDistance(touch1, touch2) {
        return Math.sqrt(
            Math.pow(touch2.currentX - touch1.currentX, 2) +
            Math.pow(touch2.currentY - touch1.currentY, 2)
        );
    }
    
    clearLongPressTimer() {
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
        if (this.twoFingerLongPressTimer) {
            clearTimeout(this.twoFingerLongPressTimer);
            this.twoFingerLongPressTimer = null;
        }
    }
    
    destroy() {
        // Clean up event listeners
        this.element.removeEventListener('touchstart', this.handleTouchStart);
        this.element.removeEventListener('touchmove', this.handleTouchMove);
        this.element.removeEventListener('touchend', this.handleTouchEnd);
        this.element.removeEventListener('touchcancel', this.handleTouchCancel);
        
        this.clearLongPressTimer();
        this.touches.clear();
        
        console.log('🤏 Touch gesture manager destroyed');
    }
}

// Export for use in main application
window.TouchGestureManager = TouchGestureManager;