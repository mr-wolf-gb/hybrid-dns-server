import React, { useState, useEffect } from 'react';
import { XMarkIcon, DocumentArrowDownIcon } from '@heroicons/react/24/outline';
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

interface ReportGenerateModalProps {
  isOpen: boolean;
  onClose: () => void;
  templates: ReportTemplate[];
}

const ReportGenerateModal: React.FC<ReportGenerateModalProps> = ({
  isOpen,
  onClose,
  templates
}) => {
  const [formData, setFormData] = useState({
    template_id: '',
    parameters: '{}',
    start_date: '',
    end_date: '',
    export_format: 'html'
  });
  const [loading, setLoading] = useState(false);
  const [parametersError, setParametersError] = useState('');
  const [generatedReport, setGeneratedReport] = useState<any>(null);

  useEffect(() => {
    if (isOpen) {
      // Set default date range (last 7 days)
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 7);
      
      setFormData({
        template_id: '',
        parameters: '{}',
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
        export_format: 'html'
      });
      setGeneratedReport(null);
      setParametersError('');
    }
  }, [isOpen]);

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

  const handleTemplateChange = (templateId: string) => {
    const template = templates.find(t => t.template_id === templateId);
    if (template) {
      setFormData(prev => ({
        ...prev,
        template_id: templateId,
        parameters: JSON.stringify(template.parameters, null, 2)
      }));
      validateParameters(JSON.stringify(template.parameters, null, 2));
    } else {
      setFormData(prev => ({
        ...prev,
        template_id: templateId,
        parameters: '{}'
      }));
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateParameters(formData.parameters)) {
      return;
    }

    setLoading(true);
    try {
      const reportData = {
        template_id: formData.template_id,
        parameters: JSON.parse(formData.parameters),
        start_date: formData.start_date ? new Date(formData.start_date).toISOString() : undefined,
        end_date: formData.end_date ? new Date(formData.end_date).toISOString() : undefined
      };

      const response = await reportsApi.generateReport(reportData);
      setGeneratedReport(response.data);
      toast.success('Report generated successfully');
    } catch (error: any) {
      console.error('Failed to generate report:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!generatedReport) return;

    setLoading(true);
    try {
      const exportData = {
        template_id: formData.template_id,
        format: formData.export_format,
        parameters: JSON.parse(formData.parameters),
        start_date: formData.start_date ? new Date(formData.start_date).toISOString() : undefined,
        end_date: formData.end_date ? new Date(formData.end_date).toISOString() : undefined
      };

      const response = await reportsApi.exportReport(exportData);
      
      // Create download link
      const blob = new Blob([response.data], { 
        type: response.headers['content-type'] || 'application/octet-stream' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from Content-Disposition header or create default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `report_${formData.template_id}_${new Date().toISOString().split('T')[0]}.${formData.export_format}`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Report exported successfully');
    } catch (error: any) {
      console.error('Failed to export report:', error);
      toast.error(error.response?.data?.detail || 'Failed to export report');
    } finally {
      setLoading(false);
    }
  };

  const selectedTemplate = templates.find(t => t.template_id === formData.template_id);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Generate Report</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Configuration Panel */}
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900">Report Configuration</h3>
              
              <form onSubmit={handleGenerate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Report Template
                  </label>
                  <select
                    value={formData.template_id}
                    onChange={(e) => handleTemplateChange(e.target.value)}
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

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={formData.start_date}
                      onChange={(e) => setFormData(prev => ({ ...prev, start_date: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={formData.end_date}
                      onChange={(e) => setFormData(prev => ({ ...prev, end_date: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Parameters (JSON)
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
                </div>

                <button
                  type="submit"
                  disabled={loading || !!parametersError || !formData.template_id}
                  className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Generating...' : 'Generate Report'}
                </button>
              </form>

              {generatedReport && (
                <div className="border-t pt-4">
                  <h4 className="text-md font-medium text-gray-900 mb-3">Export Options</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Export Format
                      </label>
                      <select
                        value={formData.export_format}
                        onChange={(e) => setFormData(prev => ({ ...prev, export_format: e.target.value }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="html">HTML</option>
                        <option value="pdf">PDF</option>
                        <option value="csv">CSV</option>
                        <option value="json">JSON</option>
                        <option value="txt">Text</option>
                      </select>
                    </div>
                    <button
                      onClick={handleExport}
                      disabled={loading}
                      className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                    >
                      <DocumentArrowDownIcon className="h-4 w-4" />
                      <span>{loading ? 'Exporting...' : 'Export Report'}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Preview Panel */}
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900">Report Preview</h3>
              
              {generatedReport ? (
                <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="mb-4">
                    <h4 className="font-medium text-gray-900">{generatedReport.template_name}</h4>
                    <p className="text-sm text-gray-500">
                      Generated: {new Date(generatedReport.generated_at).toLocaleString()}
                    </p>
                    {generatedReport.start_date && generatedReport.end_date && (
                      <p className="text-sm text-gray-500">
                        Period: {new Date(generatedReport.start_date).toLocaleDateString()} - {new Date(generatedReport.end_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <div className="bg-white border rounded p-3 max-h-96 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap font-mono">
                      {generatedReport.content}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="border border-gray-200 rounded-lg p-8 text-center text-gray-500">
                  <DocumentArrowDownIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Generate a report to see the preview here</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex justify-end space-x-3 p-6 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReportGenerateModal;