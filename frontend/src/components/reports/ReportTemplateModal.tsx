import React, { useState, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
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

interface ReportTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  template?: ReportTemplate | null;
}

const ReportTemplateModal: React.FC<ReportTemplateModalProps> = ({
  isOpen,
  onClose,
  template
}) => {
  const [formData, setFormData] = useState({
    template_id: '',
    name: '',
    description: '',
    template_content: '',
    parameters: '{}'
  });
  const [loading, setLoading] = useState(false);
  const [parametersError, setParametersError] = useState('');

  useEffect(() => {
    if (template) {
      setFormData({
        template_id: template.template_id,
        name: template.name,
        description: template.description,
        template_content: template.template_content,
        parameters: JSON.stringify(template.parameters, null, 2)
      });
    } else {
      setFormData({
        template_id: '',
        name: '',
        description: '',
        template_content: '',
        parameters: '{}'
      });
    }
    setParametersError('');
  }, [template, isOpen]);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateParameters(formData.parameters)) {
      return;
    }

    setLoading(true);
    try {
      const templateData = {
        ...formData,
        parameters: JSON.parse(formData.parameters)
      };

      if (template) {
        await reportsApi.updateTemplate(template.template_id, templateData);
        toast.success('Template updated successfully');
      } else {
        await reportsApi.createTemplate(templateData);
        toast.success('Template created successfully');
      }
      
      onClose();
    } catch (error: any) {
      console.error('Failed to save template:', error);
      toast.error(error.response?.data?.detail || 'Failed to save template');
    } finally {
      setLoading(false);
    }
  };

  const defaultTemplate = `# {{ template_name }} Report
Generated: {{ report_date }}
Period: {{ start_date }} to {{ end_date }}

## Summary
- Total Items: {{ total_items }}
- Active Items: {{ active_items }}

## Details
{% for item in items %}
- {{ item.name }}: {{ item.value }}
{% endfor %}`;

  const handleUseDefaultTemplate = () => {
    setFormData(prev => ({
      ...prev,
      template_content: defaultTemplate
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            {template ? 'Edit Report Template' : 'Create Report Template'}
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
                  Template ID
                </label>
                <input
                  type="text"
                  value={formData.template_id}
                  onChange={(e) => setFormData(prev => ({ ...prev, template_id: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., zone_summary"
                  required
                  disabled={!!template}
                />
                {template && (
                  <p className="text-xs text-gray-500 mt-1">Template ID cannot be changed</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Template Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., DNS Zone Summary Report"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Brief description of what this report contains"
                required
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Template Content (Jinja2)
                </label>
                <button
                  type="button"
                  onClick={handleUseDefaultTemplate}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Use Default Template
                </button>
              </div>
              <textarea
                value={formData.template_content}
                onChange={(e) => setFormData(prev => ({ ...prev, template_content: e.target.value }))}
                rows={12}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                placeholder="Enter Jinja2 template content..."
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Use Jinja2 syntax for dynamic content. Available variables depend on the report type.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Default Parameters (JSON)
              </label>
              <textarea
                value={formData.parameters}
                onChange={(e) => handleParametersChange(e.target.value)}
                rows={6}
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
                Default parameters for this template in JSON format
              </p>
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
              {loading ? 'Saving...' : (template ? 'Update Template' : 'Create Template')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReportTemplateModal;