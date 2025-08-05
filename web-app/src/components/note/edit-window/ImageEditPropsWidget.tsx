// ImageEditPropsWidget.tsx
import React, { useRef, useState, useEffect } from 'react';
import { SerializedNote } from '../../../model/Note';
import './ImageEditPropsWidget.css';
import { PametTabIndex } from '../../../core/constants';
import { pamet } from '../../../core/facade';
import { MediaItem } from '../../../model/MediaItem';
import { getLogger } from 'fusion/logging';
import { parseClipboardContents, toUriFriendlyFileName } from '../../../util';

let log = getLogger('ImageEditPropsWidget');

interface ImageEditPropsWidgetProps {
    noteData: SerializedNote;
    setNoteImage: (blob: Blob, path: string) => Promise<void>;
    removeNoteImage: () => Promise<void>;
}

export const ImageEditPropsWidget: React.FC<ImageEditPropsWidgetProps> = ({ noteData, setNoteImage, removeNoteImage }) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const dropZoneRef = useRef<HTMLDivElement>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isDraggingOver, setIsDraggingOver] = useState(false);

    const loadImage = async (file: File) => {
        if (!file.type.startsWith('image/')) {
            log.warning('Dropped file is not an image:', file.type);
            return;
        }
        setIsLoading(true);
        try {
            if (noteData.content.image) {  // If an image is already present
                await removeNoteImage();
            }
            await setNoteImage(file, file.name);
        } catch (error: any) {
            log.error('Error setting note image:', error);
            alert(`Error: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    }

    const handleUploadFileClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            loadImage(file).catch(error => {
                log.error('Error processing file in handleFileChange:', error);
            });
        }
        event.target.value = ''; // Clear the file input
    };

    const handleDragEnter = (event: React.DragEvent) => {
        event.preventDefault();
        event.stopPropagation();
        setIsDraggingOver(true);
    };

    const handleDragLeave = (event: React.DragEvent) => {
        event.preventDefault();
        event.stopPropagation();
        setIsDraggingOver(false);
    };

    const handleDragOver = (event: React.DragEvent) => {
        event.preventDefault();
        event.stopPropagation(); // Necessary to allow drop
    };

    const handleDrop = (event: React.DragEvent) => {
        event.preventDefault();
        event.stopPropagation();
        setIsDraggingOver(false);

        if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
            if (event.dataTransfer.files.length > 1) {
                alert('Only one image can be dropped at a time.');
                return;
            }
            const file = event.dataTransfer.files[0];
            loadImage(file).catch(error => {
                log.error('Error processing file in handleDrop:', error);
            });
            event.dataTransfer.clearData();
        }
    };

    const handlePaste = async (event: React.ClipboardEvent) => {
        const clipboardItems = await parseClipboardContents();
        for (const item of clipboardItems) {
            if (item.type === 'image' && item.image_blob) {
                // The blob doesn't have a name, so we'll create one.
                const fileName = `pasted-image.${item.image_blob.type.split('/')[1]}`;
                await loadImage(new File([item.image_blob], fileName, { type: item.image_blob.type }));
                break; // Process only the first image found
            }
        }
    };


    const handleFocus = (e: React.FocusEvent) => {
        e.stopPropagation();
        log.info('Drop zone focused');
    };

    const handleBlur = (e: React.FocusEvent) => {
        e.stopPropagation();
        log.info('Drop zone blurred');
    };

    const handleAddFromUrl = async () => {
        const url = window.prompt("Please enter the image URL:");
        if (!url) {
            return;
        }

        setIsLoading(true);
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch image. Status: ${response.status}`);
            }
            const blob = await response.blob();
            if (!blob.type.startsWith('image/')) {
                alert('The provided URL does not point to a valid image.');
                return;
            }

            let fileName = url.substring(url.lastIndexOf('/') + 1) || 'downloaded-image';
            fileName = toUriFriendlyFileName(fileName);
            await loadImage(new File([blob], fileName, { type: blob.type }));

        } catch (error) {
            log.error('Error fetching image from URL:', error);
            alert('Failed to fetch image from the provided URL. This might be due to browser security restrictions (CORS). Please download the image to your computer and upload it manually. The upcoming desktop app will not have this limitation.');
        } finally {
            setIsLoading(false);
        }
    }

    let imageUrl = '';
    if (noteData.content.image) {
        const mediaItem = new MediaItem(noteData.content.image);
        const route = mediaItem.pametRoute(pamet.appViewState.userId!, pamet.appViewState.currentProjectId!);
        route.host = window.location.host;
        route.protocol = window.location.protocol;
        imageUrl = route.toString();
    }

    const dropZoneClasses = ['image-preview-container'];
    if (isDraggingOver) {
        dropZoneClasses.push('dragging-over');
    }

    const imagePresent = !!imageUrl;

    return (
        <div className="image-edit-props-widget">
            <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileChange}
                accept="image/*"
                disabled={imagePresent}
            />
            <div className='buttons-container'>
                <button
                    className='action-button'
                    onClick={handleUploadFileClick}
                    disabled={isLoading}
                    tabIndex={PametTabIndex.NoteEditViewWidget1 + 9}
                >
                    {isLoading ? 'Uploading...' : 'Upload file'}
                </button>
                <button
                    className='action-button'
                    onClick={handleAddFromUrl}
                    disabled={isLoading}
                    tabIndex={PametTabIndex.NoteEditViewWidget1 + 10}
                >Add from URL</button>
                <button
                    className='action-button'
                    onClick={() => alert('This feature is not yet implemented, sorry :)')}
                    disabled={isLoading}
                    tabIndex={PametTabIndex.NoteEditViewWidget1 + 11}
                >New image</button>
            </div>
            <div
                ref={dropZoneRef}
                className={dropZoneClasses.join(' ')}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                tabIndex={PametTabIndex.NoteEditViewWidget1 + 8} // Make it focusable for paste events
                onPaste={handlePaste}
                onFocus={handleFocus}
                onBlur={handleBlur}
            >
                {!isLoading && !imagePresent &&
                    <div className="image-preview-placeholder">
                        <span>Drop or paste image</span>
                    </div>
                }
                {isLoading && <div>Loading...</div>}
                {imagePresent &&
                    <img src={imageUrl} alt="preview" style={{ maxWidth: '100%', maxHeight: '100px' }} />
                }
                {imagePresent &&
                    <button onClick={removeNoteImage} className="remove-image-button action-button">
                        X
                    </button>
                }

            </div>
        </div>
    );
};
