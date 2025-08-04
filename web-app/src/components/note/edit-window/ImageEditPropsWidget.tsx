// ImageEditPropsWidget.tsx
import React, { useRef, useState } from 'react';
import { SerializedNote } from '../../../model/Note';
import './ImageEditPropsWidget.css';
import { pamet } from '../../../core/facade';
import { MediaItem } from '../../../model/MediaItem';
import { getLogger } from 'fusion/logging';

let log = getLogger('ImageEditPropsWidget');

interface ImageEditPropsWidgetProps {
    noteData: SerializedNote;
    setNoteImage: (blob: Blob, path: string) => Promise<void>;
}

export const ImageEditPropsWidget: React.FC<ImageEditPropsWidgetProps> = ({ noteData, setNoteImage }) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isLoading, setIsLoading] = useState(false);

    const handleUploadFileClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setIsLoading(true);
            try {
                await setNoteImage(file, file.name);
            } catch (error) {
                log.error('Error setting note image:', error);
            } finally {
                setIsLoading(false);
            }
        }
        // Clear the file input so the same file can be selected again
        event.target.value = '';
    };

    const handleAddFromUrl = () => {
        // Placeholder for add from URL logic
        console.log('Add from URL');
    }

    let imageUrl = '';
    if (noteData.content.image) {
        const mediaItem = new MediaItem(noteData.content.image);
        const route = mediaItem.pametRoute(pamet.appViewState.userId!, pamet.appViewState.currentProjectId!);
        route.host = window.location.host;
        route.protocol = window.location.protocol;
        imageUrl = route.toString();
    }

    return (
        <div className="image-edit-props-widget">
            <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileChange}
                accept="image/*"
            />
            <div className='buttons-container'>
                <button className='action-button' onClick={handleUploadFileClick} disabled={isLoading}>
                    {isLoading ? 'Uploading...' : 'Upload file'}
                </button>
                <button className='action-button' onClick={handleAddFromUrl}>Add from URL</button>
                <button className='action-button' onClick={() => console.log('New image')}>New image</button>
            </div>
            <div className="image-preview-container">
                {isLoading && <div>Loading...</div>}
                {!isLoading && imageUrl &&
                    <img src={imageUrl} alt="preview" style={{ maxWidth: '100%', maxHeight: '100px' }} />
                }
                {!isLoading && !imageUrl &&
                    <div className="image-preview-placeholder">
                        <span>Drop image here</span>
                    </div>
                }
            </div>
        </div>
    );
};
