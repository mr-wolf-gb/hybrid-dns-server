import React, { useState, useEffect } from 'react';
import { XMarkIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';
import { reportsApi } from '../../services/api';

interface ReportTemplate {
  template_id: string;
  name: string;
  description: string;
  template_content: string;
  parameters: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface ReportSchedule {
  schedule_id: string;
  template_id: string;
  name: string;
  frequency: string;
  parameters: Record<string, any>;
  recipients: string[];
  enabled: boolean;
  created_at: string;
  last_run?: string;
  next_run?: string;
}

interface ReportScheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  schedule?: ReportSchedule | null;
  templates: ReportTemplate[];
}

const ReportScheduleModal: React.FC<ReportScheduleModalProps> = ({
  isOpen,
  onClose,
  schedule,
  templates
}) => {
  const [formData, setFormData] = useState({
    schedule_id: '',
    template_id: '',
    name: '',
    frequency: 'weekly',
    parameters: '{}',
    recipients: [''],
    enabled: true
  });
  const [loading, setLoading] = useState(false);
  const [parametersError, setParametersError] = useState('');

  useEffect(() => {
    if (schedule) {
      setFormData({
        schedule_id: schedule.schedule_id,
        template_id: schedule.template_id,
        name: schedule.name,
        frequency: schedule.frequency,
        parameters: JSON.stringify(schedule.parameters, null, 2),
        recipients: schedule.recipients.length > 0 ? schedule.recipients : [''],
        enabled: schedule.enabled
      });
    } else {
      setFormData({
        schedule_id: '',
        template_id: '',
        name: '',
        frequency: 'weekly',
        parameters: '{}',
        recipients: [''],
        enabled: true
      });
    }
    setParametersError('');
  }, [schedule, isOpen]);

  const validateParameters = (parametersStr: string) => {
    try {
      JSON.parse(parametersStr);
      setParametersError('');
      return true;
    } catch (error) {
      setParametersError('Invalid JSON format');
      return false;
    }
  };

  const handleParametersChange = (value: string) => {
    setFormData(prev => ({ ...prev, parameters: value }));
    validateParameters(value);
  };

  const handleRecipientChange = (index: number, value: string) => {
    const newRecipients = [...formData.recipients];
    newRecipients[index] = value;
    setFormData(prev => ({ ...prev, recipients: newRecipients }));
  };

  const addRecipient = () => {
    setFormData(prev => ({
      ...prev,
      recipients: [...prev.recipients, '']
    }));
  };

  const removeRecipient = (index: number) => {
    if (formData.recipients.length > 1) {
      const newRecipients = formData.recipients.filter((_, i) => i !== index);
      setFormData(prev => ({ ...prev, recipients: newRecipients }));
    }
  };

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateParameters(formData.parameters)) {
      return;
    }

    // Validate recipients
    const validRecipients = formData.recipients.filter(email => email.trim() !== '');
    if (validRecipients.length === 0) {
      toast.error('At least one recipient is required');
      return;
    }

    for (const email of validRecipients) {
      if (!validateEmail(email)) {
        toast.error(`Invalid email address: ${email}`);
        return;
      }
    }

    setLoading(true);
    try {
      const scheduleData = {
        ...formData,
        parameters: JSON.parse(formData.parameters),
        recipients: validRecipients
      };

      if (schedule) {
        await reportsApi.updateSchedule(schedule.schedule_id, scheduleData);
        toast.success('Schedule updated successfully');
      } else {
        await reportsApi.createSchedule(scheduleData);
        toast.success('Schedule created successfully');
      }
      
      onClose();
    } catch (error: any) {
      console.error('Failed to save schedule:', error);
      toast.error(error.response?.data?.detail || 'Failed to save schedule');
    } finally {
      setLoading(false);
    }
  };

  const selectedTemplate = templates.find(t => t.template_id === formData.template_id);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {schedule ? 'Edit Report Schedule' : 'Create Report Schedule'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Schedule ID
                </label>
                <input
                  type="text"
                  value={formData.schedule_id}
                  onChange={(e) => setFormData(prev => ({ ...prev, schedule_id: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., weekly_zone_report"
                  required
                  disabled={!!schedule}
                />
                {schedule && (
                  <p className="text-xs text-gray-500 mt-1">Schedule ID cannot be changed</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Schedule Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Weekly DNS Zone Report"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Report Template
                </label>
                <select
                  value={formData.template_id}
                  onChange={(e) => setFormData(prev => ({ ...prev, template_id: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select a template</option>
                  {templates.map((template) => (
                    <option key={template.template_id} value={template.template_id}>
                      {template.name}
                    </option>
                  ))}
                </select>
                {selectedTemplate && (
                  <p className="text-xs text-gray-500 mt-1">{selectedTemplate.description}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Frequency
                </label>
                <select
                  value={formData.frequency}
                  onChange={(e) => setFormData(prev => ({ ...prev, frequency: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Recipients
              </label>
              <div className="space-y-2">
                {formData.recipients.map((recipient, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="email"
                      value={recipient}
                      onChange={(e) => handleRecipientChange(index, e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="email@example.com"
                      required={index === 0}
                    />
                    {formData.recipients.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeRecipient(index)}
                        className="text-red-600 hover:text-red-800"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addRecipient}
                  className="flex items-center space-x-1 text-blue-600 hover:text-blue-800 text-sm"
                >
                  <PlusIcon className="h-4 w-4" />
                  <span>Add Recipient</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Parameters (JSON)
              </label>
              <textarea
                value={formData.parameters}
                onChange={(e) => handleParametersChange(e.target.value)}
                rows={4}
                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 font-mono text-sm ${
                  parametersError 
                    ? 'border-red-300 focus:ring-red-500' 
                    : 'border-gray-300 focus:ring-blue-500'
                }`}
                placeholder='{"include_inactive": false, "limit": 10}'
              />
              {parametersError && (
                <p className="text-sm text-red-600 mt-1">{parametersError}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                Override template parameters for this schedule
              </p>
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={(e) => setFormData(prev => ({ ...prev, enabled: e.target.checked }))}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="enabled" className="ml-2 block text-sm text-gray-900">
                Enable this schedule
              </label>
            </div>
          </div>

          <div className="flex justify-end space-x-3 mt-8 pt-6 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !!parametersError}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Saving...' : (schedule ? 'Update Schedule' : 'Create Schedule')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReportScheduleModal;