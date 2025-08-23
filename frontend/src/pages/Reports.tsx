import React, { useState, useEffect } from 'react';
import {
  DocumentTextIcon,
  ClockIcon,
  ChartBarIcon,
  DocumentArrowDownIcon,
  PlusIcon,
  PlayIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/react/24/outline';
import { toast } from 'react-toastify';

import { reportsApi } from '../services/api';
import ReportTemplateModal from '../components/reports/ReportTemplateModal';
import ReportScheduleModal from '../components/reports/ReportScheduleModal';
import ReportGenerateModal from '../components/reports/ReportGenerateModal';
import AnalyticsDashboard from '../components/reports/AnalyticsDashboard';

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

const Reports: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'templates' | 'schedules' | 'analytics'>('templates');
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [schedules, setSchedules] = useState<ReportSchedule[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ReportTemplate | null>(null);
  const [editingSchedule, setEditingSchedule] = useState<ReportSchedule | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [templatesResponse, schedulesResponse] = await Promise.all([
        reportsApi.getTemplates(),
        reportsApi.getSchedules()
      ]);

      setTemplates(templatesResponse.data);
      setSchedules(schedulesResponse.data);
    } catch (error) {
      console.error('Failed to load reports data:', error);
      toast.error('Failed to load reports data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = () => {
    setEditingTemplate(null);
    setTemplateModalOpen(true);
  };

  const handleEditTemplate = (template: ReportTemplate) => {
    setEditingTemplate(template);
    setTemplateModalOpen(true);
  };

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      await reportsApi.deleteTemplate(templateId);
      toast.success('Template deleted successfully');
      loadData();
    } catch (error) {
      console.error('Failed to delete template:', error);
      toast.error('Failed to delete template');
    }
  };

  const handleCreateSchedule = () => {
    setEditingSchedule(null);
    setScheduleModalOpen(true);
  };

  const handleEditSchedule = (schedule: ReportSchedule) => {
    setEditingSchedule(schedule);
    setScheduleModalOpen(true);
  };

  const handleDeleteSchedule = async (scheduleId: string) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;

    try {
      await reportsApi.deleteSchedule(scheduleId);
      toast.success('Schedule deleted successfully');
      loadData();
    } catch (error) {
      console.error('Failed to delete schedule:', error);
      toast.error('Failed to delete schedule');
    }
  };

  const handleRunSchedule = async (scheduleId: string) => {
    try {
      await reportsApi.runSchedule(scheduleId);
      toast.success('Report schedule executed successfully');
      loadData();
    } catch (error) {
      console.error('Failed to run schedule:', error);
      toast.error('Failed to run schedule');
    }
  };

  const handleTemplateModalClose = () => {
    setTemplateModalOpen(false);
    setEditingTemplate(null);
    loadData();
  };

  const handleScheduleModalClose = () => {
    setScheduleModalOpen(false);
    setEditingSchedule(null);
    loadData();
  };

  const handleGenerateModalClose = () => {
    setGenerateModalOpen(false);
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Invalid date';
      return date.toLocaleString();
    } catch (error) {
      return 'Invalid date';
    }
  };

  const getFrequencyBadgeColor = (frequency: string) => {
    switch (frequency) {
      case 'daily': return 'bg-green-100 text-green-800';
      case 'weekly': return 'bg-blue-100 text-blue-800';
      case 'monthly': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
        <div className="flex space-x-3">
          {activeTab === 'templates' && (
            <button
              onClick={handleCreateTemplate}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
            >
              <PlusIcon className="h-4 w-4" />
              <span>New Template</span>
            </button>
          )}
          {activeTab === 'schedules' && (
            <button
              onClick={handleCreateSchedule}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
            >
              <PlusIcon className="h-4 w-4" />
              <span>New Schedule</span>
            </button>
          )}
          <button
            onClick={() => setGenerateModalOpen(true)}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center space-x-2"
          >
            <DocumentArrowDownIcon className="h-4 w-4" />
            <span>Generate Report</span>
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('templates')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'templates'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <DocumentTextIcon className="h-5 w-5 inline mr-2" />
            Templates
          </button>
          <button
            onClick={() => setActiveTab('schedules')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'schedules'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <ClockIcon className="h-5 w-5 inline mr-2" />
            Schedules
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'analytics'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <ChartBarIcon className="h-5 w-5 inline mr-2" />
            Analytics
          </button>
        </nav>
      </div>

      {/* Templates Tab */}
      {activeTab === 'templates' && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Report Templates</h2>
            <p className="text-sm text-gray-500">Manage customizable report templates</p>
          </div>
          <div className="divide-y divide-gray-200">
            {templates.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                No report templates found. Create your first template to get started.
              </div>
            ) : (
              templates.map((template) => (
                <div key={template.template_id} className="p-6 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900">{template.name}</h3>
                      <p className="text-sm text-gray-500 mt-1">{template.description}</p>
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-400">
                        <span>ID: {template.template_id}</span>
                        <span>Created: {formatDate(template.created_at)}</span>
                        <span>Updated: {formatDate(template.updated_at)}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleEditTemplate(template)}
                        className="text-blue-600 hover:text-blue-800"
                        title="Edit Template"
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteTemplate(template.template_id)}
                        className="text-red-600 hover:text-red-800"
                        title="Delete Template"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Schedules Tab */}
      {activeTab === 'schedules' && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Report Schedules</h2>
            <p className="text-sm text-gray-500">Manage automated report generation schedules</p>
          </div>
          <div className="divide-y divide-gray-200">
            {schedules.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                No report schedules found. Create your first schedule to automate report generation.
              </div>
            ) : (
              schedules.map((schedule) => (
                <div key={schedule.schedule_id} className="p-6 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <h3 className="text-lg font-medium text-gray-900">{schedule.name}</h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getFrequencyBadgeColor(schedule.frequency)}`}>
                          {schedule.frequency}
                        </span>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${schedule.enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                          {schedule.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">Template: {schedule.template_id}</p>
                      <p className="text-sm text-gray-500">Recipients: {schedule.recipients.join(', ')}</p>
                      <div className="flex items-center space-x-4 mt-2 text-xs text-gray-400">
                        <span>Last Run: {formatDate(schedule.last_run)}</span>
                        <span>Next Run: {formatDate(schedule.next_run)}</span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleRunSchedule(schedule.schedule_id)}
                        className="text-green-600 hover:text-green-800"
                        title="Run Now"
                      >
                        <PlayIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleEditSchedule(schedule)}
                        className="text-blue-600 hover:text-blue-800"
                        title="Edit Schedule"
                      >
                        <PencilIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteSchedule(schedule.schedule_id)}
                        className="text-red-600 hover:text-red-800"
                        title="Delete Schedule"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <AnalyticsDashboard />
      )}

      {/* Modals */}
      {templateModalOpen && (
        <ReportTemplateModal
          isOpen={templateModalOpen}
          onClose={handleTemplateModalClose}
          template={editingTemplate}
        />
      )}

      {scheduleModalOpen && (
        <ReportScheduleModal
          isOpen={scheduleModalOpen}
          onClose={handleScheduleModalClose}
          schedule={editingSchedule}
          templates={templates}
        />
      )}

      {generateModalOpen && (
        <ReportGenerateModal
          isOpen={generateModalOpen}
          onClose={handleGenerateModalClose}
          templates={templates}
        />
      )}
    </div>
  );
};

export default Reports;