import React, { useState, useEffect } from 'react';
import { 
  ClockIcon as Clock, 
  ExclamationTriangleIcon as AlertTriangle, 
  CheckCircleIcon as CheckCircle, 
  ArrowPathIcon as RotateCcw, 
  InformationCircleIcon as Info,
  TrashIcon as Trash2 
} from '@heroicons/react/24/outline';

interface RollbackCandidate {
  backup_id: string;
  type: string;
  description: string;
  timestamp: string;
  size: number;
  rollback_method: string;
  zone_name?: string;
  rpz_zone?: string;
}

interface SafetyResult {
  safe: boolean;
  errors: string[];
  warnings: string[];
  backup_info?: any;
  estimated_downtime?: string;
}

const RollbackManager: React.FC = () => {
  const [candidates, setCandidates] = useState<RollbackCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [rollbackType, setRollbackType] = useState('all');
  const [selectedCandidate, setSelectedCandidate] = useState<RollbackCandidate | null>(null);
  const [safetyResult, setSafetyResult] = useState<SafetyResult | null>(null);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  useEffect(() => {
    fetchRollbackCandidates();
  }, [rollbackType]);

  const fetchRollbackCandidates = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/rollback/candidates?rollback_type=${rollbackType}`);
      const data = await response.json();
      setCandidates(data.candidates || []);
    } catch (error) {
      console.error('Failed to fetch rollback candidates:', error);
    } finally {
      setLoading(false);
    }
  };

  const testRollbackSafety = async (backupId: string) => {
    try {
      const response = await fetch(`/api/rollback/test/${backupId}`, {
        method: 'POST'
      });
      const result = await response.json();
      setSafetyResult(result);
    } catch (error) {
      console.error('Failed to test rollback safety:', error);
      setSafetyResult({
        safe: false,
        errors: ['Failed to test rollback safety'],
        warnings: []
      });
    }
  };

  const performRollback = async (candidate: RollbackCandidate) => {
    try {
      setIsRollingBack(true);
      let endpoint = '';
      
      switch (candidate.type) {
        case 'full_configuration':
          endpoint = `/api/rollback/configuration/${candidate.backup_id}`;
          break;
        case 'zone_file':
          endpoint = `/api/rollback/zone/${candidate.zone_name}?backup_id=${candidate.backup_id}`;
          break;
        case 'rpz_file':
          endpoint = `/api/rollback/rpz/${candidate.rpz_zone}?backup_id=${candidate.backup_id}`;
          break;
        case 'forwarder_configuration':
          endpoint = `/api/rollback/forwarders?backup_id=${candidate.backup_id}`;
          break;
        default:
          throw new Error(`Unknown rollback type: ${candidate.type}`);
      }

      const response = await fetch(endpoint, {
        method: 'POST'
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Rollback completed successfully: ${result.message}`);
        setShowConfirmDialog(false);
        setSelectedCandidate(null);
        setSafetyResult(null);
        fetchRollbackCandidates(); // Refresh the list
      } else {
        const error = await response.json();
        throw new Error(error.detail?.message || error.detail || 'Rollback failed');
      }
    } catch (error) {
      console.error('Rollback failed:', error);
      alert(`Rollback failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsRollingBack(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatTimestamp = (timestamp: string): string => {
    return new Date(timestamp).toLocaleString();
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'full_configuration':
        return '🔧';
      case 'zone_file':
        return '🌐';
      case 'rpz_file':
        return '🛡️';
      case 'forwarder_configuration':
        return '↗️';
      default:
        return '📄';
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'full_configuration':
        return 'Full Configuration';
      case 'zone_file':
        return 'DNS Zone';
      case 'rpz_file':
        return 'RPZ Security';
      case 'forwarder_configuration':
        return 'Forwarders';
      default:
        return type;
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
            Configuration Rollback Manager
          </h3>
          
          {/* Filter Controls */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rollback Type
            </label>
            <select
              value={rollbackType}
              onChange={(e) => setRollbackType(e.target.value)}
              className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
            >
              <option value="all">All Types</option>
              <option value="full">Full Configuration</option>
              <option value="zone">DNS Zones</option>
              <option value="rpz">RPZ Security</option>
              <option value="forwarder">Forwarders</option>
            </select>
          </div>

          {/* Candidates List */}
          {loading ? (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-500">Loading rollback candidates...</p>
            </div>
          ) : candidates.length === 0 ? (
            <div className="text-center py-8">
              <Clock className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No rollback candidates</h3>
              <p className="mt-1 text-sm text-gray-500">
                No backups available for the selected type.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {candidates.map((candidate) => (
                <div
                  key={candidate.backup_id}
                  className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{getTypeIcon(candidate.type)}</span>
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">
                          {getTypeLabel(candidate.type)}
                          {candidate.zone_name && ` - ${candidate.zone_name}`}
                          {candidate.rpz_zone && ` - ${candidate.rpz_zone}`}
                        </h4>
                        <p className="text-sm text-gray-500">{candidate.description}</p>
                        <div className="flex items-center space-x-4 mt-1 text-xs text-gray-400">
                          <span>{formatTimestamp(candidate.timestamp)}</span>
                          <span>{formatFileSize(candidate.size)}</span>
                          <span className="font-mono">{candidate.backup_id}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => {
                          setSelectedCandidate(candidate);
                          testRollbackSafety(candidate.backup_id);
                        }}
                        className="inline-flex items-center px-3 py-1 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        <Info className="h-3 w-3 mr-1" />
                        Test Safety
                      </button>
                      <button
                        onClick={() => {
                          setSelectedCandidate(candidate);
                          testRollbackSafety(candidate.backup_id);
                          setShowConfirmDialog(true);
                        }}
                        className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        <RotateCcw className="h-3 w-3 mr-1" />
                        Rollback
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Safety Test Results */}
      {safetyResult && selectedCandidate && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Rollback Safety Test Results
            </h3>
            
            <div className="space-y-4">
              <div className={`flex items-center space-x-2 ${safetyResult.safe ? 'text-green-600' : 'text-red-600'}`}>
                {safetyResult.safe ? (
                  <CheckCircle className="h-5 w-5" />
                ) : (
                  <AlertTriangle className="h-5 w-5" />
                )}
                <span className="font-medium">
                  {safetyResult.safe ? 'Safe to rollback' : 'Rollback not recommended'}
                </span>
              </div>

              {safetyResult.errors.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-red-800 mb-2">Errors:</h4>
                  <ul className="list-disc list-inside space-y-1">
                    {safetyResult.errors.map((error, index) => (
                      <li key={index} className="text-sm text-red-700">{error}</li>
                    ))}
                  </ul>
                </div>
              )}

              {safetyResult.warnings.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-yellow-800 mb-2">Warnings:</h4>
                  <ul className="list-disc list-inside space-y-1">
                    {safetyResult.warnings.map((warning, index) => (
                      <li key={index} className="text-sm text-yellow-700">{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {safetyResult.estimated_downtime && (
                <div className="text-sm text-gray-600">
                  <strong>Estimated downtime:</strong> {safetyResult.estimated_downtime}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}
      {showConfirmDialog && selectedCandidate && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3 text-center">
              <AlertTriangle className="mx-auto h-12 w-12 text-yellow-400" />
              <h3 className="text-lg font-medium text-gray-900 mt-2">
                Confirm Rollback
              </h3>
              <div className="mt-2 px-7 py-3">
                <p className="text-sm text-gray-500">
                  Are you sure you want to rollback to this backup? This action cannot be undone.
                </p>
                <div className="mt-4 p-3 bg-gray-50 rounded text-left">
                  <div className="text-xs text-gray-600">
                    <div><strong>Type:</strong> {getTypeLabel(selectedCandidate.type)}</div>
                    <div><strong>Created:</strong> {formatTimestamp(selectedCandidate.timestamp)}</div>
                    <div><strong>Description:</strong> {selectedCandidate.description}</div>
                    {safetyResult?.estimated_downtime && (
                      <div><strong>Estimated downtime:</strong> {safetyResult.estimated_downtime}</div>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex justify-center space-x-3 mt-4">
                <button
                  onClick={() => {
                    setShowConfirmDialog(false);
                    setSelectedCandidate(null);
                    setSafetyResult(null);
                  }}
                  className="px-4 py-2 bg-gray-300 text-gray-800 text-sm font-medium rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-300"
                  disabled={isRollingBack}
                >
                  Cancel
                </button>
                <button
                  onClick={() => performRollback(selectedCandidate)}
                  disabled={isRollingBack || !safetyResult?.safe}
                  className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRollingBack ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white inline-block mr-2"></div>
                      Rolling back...
                    </>
                  ) : (
                    'Confirm Rollback'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RollbackManager;