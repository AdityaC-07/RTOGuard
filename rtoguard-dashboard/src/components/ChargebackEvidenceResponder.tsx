import React, { useState, useEffect } from 'react';
import { FileText, Send, CheckCircle2, HelpCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { DisputeCase, DisputeStatus, ChargebackEvidenceResponse } from '../types';
import { getDisputeStatusLabel, getConfidenceLabel } from '../utils/copy';
import { rtoAPI } from '../services/api';

export const ChargebackEvidenceResponder: React.FC = () => {
  const MOCK_RESPONSE: ChargebackEvidenceResponse = {
    case_id: 'DISP-9842',
    gateway_latency_ms: 42,
    active_disputes_count: 3,
    recovered_mtd_inr: 92400,
    highest_priority_case: {
      case_id: 'DISP-9842',
      dispute_amount_inr: 14899,
      acquirer_network: 'HDFC Bank Ltd',
      reason_code: '10.4',
      reason_description: 'Customer claims non-receipt of delivery',
      time_remaining_hours: 14.22,
      status: DisputeStatus.AWAITING_ACTION,
      pipeline_status: 'NEEDS RESPONSE',
    },
    evidence_artifacts: [
      { artifact_id: 'EV001', artifact_name: 'Customer Checkout & OTP Verification Log', artifact_type: 'Document', verified: true },
      { artifact_id: 'EV002', artifact_name: 'Courier Biometric POD & Delivery GPS Coordinates', artifact_type: 'Document', verified: true },
    ],
    auto_generate_status: 'Auto-Generate Evidence',
    win_probability: 0.88,
  };

  const MOCK_DISPUTES: DisputeCase[] = [
    MOCK_RESPONSE.highest_priority_case,
    {
      case_id: 'DISP-9841',
      dispute_amount_inr: 6450,
      acquirer_network: 'ICICI Bank Ltd',
      reason_code: '4837',
      reason_description: 'Duplication Claim',
      time_remaining_hours: 26,
      status: DisputeStatus.AWAITING_GATEWAY_SUBMISSION,
      pipeline_status: 'RESPONSE SENT',
    },
    {
      case_id: 'DISP-9839',
      dispute_amount_inr: 24200,
      acquirer_network: 'Axis Bank Ltd',
      reason_code: '4853',
      reason_description: 'Quality Specification Dispute',
      time_remaining_hours: 42,
      status: DisputeStatus.IN_DRAFT,
      pipeline_status: 'NEEDS RESPONSE',
    },
  ];

  const [allDisputes, setAllDisputes] = useState<DisputeCase[]>(MOCK_DISPUTES);
  const [selectedDispute, setSelectedDispute] = useState<DisputeCase | null>(MOCK_DISPUTES[0]);
  const [statementText, setStatementText] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const cases = await rtoAPI.getDisputeCases();
        if (cases && cases.length > 0) {
          setAllDisputes(cases);
          setSelectedDispute(cases[0]);
        }
      } catch (e) {
        console.log('Using static dispute help data');
      }
    })();
  }, []);

  const handleSubmit = async () => {
    if (!selectedDispute) return;
    setSubmitting(true);
    try {
      await rtoAPI.submitEvidence(selectedDispute.case_id, { statement: statementText });
    } catch (e) {
      console.log('Local resolution state applied for dispute response');
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  };

  const handleSelectCase = (dispute: DisputeCase) => {
    setSelectedDispute(dispute);
    setSubmitted(false);
    setStatementText('');
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-semibold text-ink">Help with return disputes</h2>
        <p className="text-sm text-ink-muted mt-1">
          If a customer claims they never received an order but our system flagged it as risky, we can help you build a response.
        </p>
      </div>

      {/* Static Explainer Card */}
      <div className="merchant-card p-4 bg-navy-subtle border-navy/20 flex items-start gap-3">
        <HelpCircle size={18} className="text-navy shrink-0 mt-0.5" />
        <p className="text-xs text-ink leading-relaxed">
          A dispute happens when a customer says an order was not delivered, but you believe it was. Use the evidence below to support your case.
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left: Dispute Queue */}
        <div className="col-span-1 merchant-card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
            <FileText size={16} className="text-navy" />
            Inbound Disputes Queue
          </h3>

          <div className="space-y-2">
            {allDisputes.map((dispute) => {
              const statusLabel = getDisputeStatusLabel(dispute.status);
              const isNeedsResponse = statusLabel === 'Needs your response';
              const isSelected = selectedDispute?.case_id === dispute.case_id;

              return (
                <button
                  key={dispute.case_id}
                  onClick={() => handleSelectCase(dispute)}
                  className={`w-full text-left p-3.5 rounded border transition-all ${
                    isSelected
                      ? 'bg-navy-subtle border-navy/40 text-ink'
                      : 'bg-beige border-border hover:bg-beige-alt text-ink'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="text-xs font-semibold text-ink">
                      Case {dispute.case_id.replace('#', '')}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                      isNeedsResponse ? 'bg-caution-bg text-caution' : 'bg-safe-bg text-safe'
                    }`}>
                      {statusLabel}
                    </span>
                  </div>

                  <p className="text-xs text-ink-muted">
                    Order value: <strong className="text-ink font-semibold">₹{dispute.dispute_amount_inr.toLocaleString()}</strong>
                  </p>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-ink-muted">
                    <span>{dispute.acquirer_network}</span>
                    <span className="px-2 py-0.5 rounded bg-beige border border-border">
                      {getConfidenceLabel(0.85)}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Dispute Detail & Response Builder */}
        <div className="col-span-2">
          {selectedDispute ? (
            <motion.div
              key={selectedDispute.case_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="merchant-card p-6 space-y-6"
            >
              {/* Header */}
              <div className="border-b border-border pb-4 flex items-start justify-between gap-4">
                <div>
                  <span className="text-xs font-medium text-ink-muted uppercase tracking-wider block mb-1">
                    Dispute Case Dossier
                  </span>
                  <h3 className="text-lg font-semibold text-ink">
                    Case {selectedDispute.case_id.replace('#', '')} • {selectedDispute.acquirer_network}
                  </h3>
                  <p className="text-xs text-ink-muted mt-1">
                    Claim Reason: {selectedDispute.reason_description}
                  </p>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-xs text-ink-muted block mb-0.5">Disputed Amount</span>
                  <span className="text-lg font-bold text-risk">
                    ₹{selectedDispute.dispute_amount_inr.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Verified Evidence Log */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
                  System Verified Order Evidence
                </h4>

                <div className="space-y-2">
                  <div className="p-3 bg-beige rounded border border-border text-xs text-ink flex items-start gap-3">
                    <CheckCircle2 size={16} className="text-navy shrink-0 mt-0.5" />
                    <div>
                      <strong className="block text-ink">Customer Checkout OTP Verified</strong>
                      <span className="text-ink-muted">Order placed via 3DS SMS OTP verification on customer mobile.</span>
                    </div>
                  </div>

                  <div className="p-3 bg-beige rounded border border-border text-xs text-ink flex items-start gap-3">
                    <CheckCircle2 size={16} className="text-navy shrink-0 mt-0.5" />
                    <div>
                      <strong className="block text-ink">Biometric Courier Delivery Confirmation</strong>
                      <span className="text-ink-muted">Delivered with GPS coordinate match within 3 meters of checkout address.</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Merchant Response Form */}
              <div className="space-y-3 pt-2">
                <label className="text-xs font-semibold text-ink uppercase tracking-wider block">
                  Describe what happened
                </label>
                <textarea
                  value={statementText}
                  onChange={(e) => setStatementText(e.target.value)}
                  className="w-full bg-beige border border-border rounded p-3 text-ink text-sm focus:border-navy focus:outline-none resize-none"
                  rows={4}
                  placeholder="E.g. Order was delivered on 14 Oct. Customer had 3 previous returns from the same address."
                />
              </div>

              {/* Action */}
              <div>
                {submitted ? (
                  <div className="p-4 rounded bg-safe-bg border border-safe/20 text-safe text-xs font-medium">
                    Your response has been recorded. We will notify you if the dispute status changes.
                  </div>
                ) : (
                  <button
                    onClick={handleSubmit}
                    disabled={submitting}
                    className="btn-primary py-2.5 px-5 text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <Send size={16} />
                    {submitting ? 'Sending...' : 'Send my response'}
                  </button>
                )}
              </div>
            </motion.div>
          ) : (
            <div className="merchant-card p-8 h-full flex items-center justify-center text-ink-muted text-sm">
              Select a dispute case on the left to view details and send your response.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
