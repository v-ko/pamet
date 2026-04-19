import React from 'react';
import '@/views/ErrorBoundary.css';

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
    state: State = { hasError: false, error: null };

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="error-boundary">
                    <h2>Something went wrong</h2>
                    <p>The app encountered an unexpected error.</p>
                    <button onClick={() => window.location.reload()}>
                        Reload
                    </button>
                    {this.state.error && (
                        <pre>{this.state.error.message}</pre>
                    )}
                </div>
            );
        }
        return this.props.children;
    }
}
