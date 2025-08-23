/**
 * WebSocket debugging component
 */

import React, { useState } from 'react';
import { testWebSocketConnection, testAllWebSocketConnections, checkWebSocketHealth } from '@/utils/websocketTest';

const WebSocketDebug: React.FC = () => {
    const [testResults, setTestResults] = useState<any>(null);
    const [healthStatus, setHealthStatus] = useState<any>(null);
    const [loading, setLoading] = useState(false);

    const handleTestSingle = async (connectionType: string) => {
        setLoading(true);
        try {
            const result = await testWebSocketConnection(connectionType);
            setTestResults({ [connectionType]: result });
        } catch (error) {
            setTestResults({ [connectionType]: { success: false, error: String(error) } });
        } finally {
            setLoading(false);
        }
    };

    const handleTestAll = async () => {
        setLoading(true);
        try {
            const results = await testAllWebSocketConnections();
            setTestResults(results);
        } catch (error) {
            setTestResults({ error: String(error) });
        } finally {
            setLoading(false);
        }
    };

    const handleHealthCheck = async () => {
        setLoading(true);
        try {
            const health = await checkWebSocketHealth();
            setHealthStatus(health);
        } catch (error) {
            setHealthStatus({ error: String(error) });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">WebSocket Debug Tools</h3>

            <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => handleTestSingle('health')}
                        disabled={loading}
                        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
                    >
                        Test Health
                    </button>
                    <button
                        onClick={() => handleTestSingle('system')}
                        disabled={loading}
                        className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                    >
                        Test System
                    </button>
                    <button
                        onClick={() => handleTestSingle('dns_management')}
                        disabled={loading}
                        className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50"
                    >
                        Test DNS
                    </button>
                    <button
                        onClick={() => handleTestSingle('security')}
                        disabled={loading}
                        className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
                    >
                        Test Security
                    </button>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={handleTestAll}
                        disabled={loading}
                        className="px-4 py-2 bg-indigo-500 text-white rounded hover:bg-indigo-600 disabled:opacity-50"
                    >
                        Test All Connections
                    </button>
                    <button
                        onClick={handleHealthCheck}
                        disabled={loading}
                        className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:opacity-50"
                    >
                        Check Service Health
                    </button>
                </div>

                {loading && (
                    <div className="text-blue-600">Testing connections...</div>
                )}

                {testResults && (
                    <div className="mt-4">
                        <h4 className="font-semibold mb-2">Test Results:</h4>
                        <pre className="bg-gray-100 dark:bg-gray-700 p-3 rounded text-sm overflow-auto">
                            {JSON.stringify(testResults, null, 2)}
                        </pre>
                    </div>
                )}

                {healthStatus && (
                    <div className="mt-4">
                        <h4 className="font-semibold mb-2">Health Status:</h4>
                        <pre className="bg-gray-100 dark:bg-gray-700 p-3 rounded text-sm overflow-auto">
                            {JSON.stringify(healthStatus, null, 2)}
                        </pre>
                    </div>
                )}
            </div>
        </div>
    );
};

export default WebSocketDebug;