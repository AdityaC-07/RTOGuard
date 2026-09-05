import React, { useState, useRef } from 'react';
import { Search, ChevronDown, ChevronUp, CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';
import { motion } from 'framer-motion';
import { RTOOrderResponse, RTODecision, OrderPayload, FormBehavior } from '../types';
import { humanizeRiskFactor, getVerdictDetails, getConfidenceLabel, scoreLabel, scoreColor, factorImpact } from '../utils/copy';
import axios from 'axios';

const BACKEND_URL = 'http://localhost:8000';

function ScoreArc({ score, color }: { score: number; color: string }) {
  const R = 52;
  const cx = 60, cy = 60;
  // Semicircle: start = left (180°), end = right (0°)
  const circumference = Math.PI * R; // half circle
  const fill = (Math.min(100, Math.max(0, score)) / 100) * circumference;
  return (
    <svg viewBox="0 0 120 64" width="120" height="64" role="img" aria-label={`Risk score ${score} out of 100`}>
      {/* track */}
      <path
        d={`M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`}
        fill="none"
        stroke="#1A3C6E"
        strokeWidth="6"
        strokeLinecap="round"
      />
      {/* fill */}
      <path
        d={`M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeLinecap="round"
        strokeDasharray={`${fill} ${circumference}`}
      />
    </svg>
  );
}

export const ReturnRiskScorer: React.FC = () => {
  const [payload, setPayload] = useState<OrderPayload>({
    order_id: 'ORD-98241',
    phone: '+91 98711 04219',
    address: 'Plot 42, Near Shiv Mandir, Gali No 3, Ext-2',
    pincode: '110086',
    order_value: 3850,
  });

  const [response, setResponse] = useState<RTOOrderResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [preset, setPreset] = useState<'verified' | 'incomplete' | 'fraud-pattern' | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [actionResolved, setActionResolved] = useState(false);
  const [otp, setOtp] = useState('');
  const [devOtp, setDevOtp] = useState('');
  const [otpVerified, setOtpVerified] = useState(false);

  // Phase 2 behavioural biometrics: how the form was filled (paste vs
  // typing, fill time, focus order). Bots paste everything in milliseconds.
  const fillStartRef = useRef<number | null>(null);
  const fieldSeqRef = useRef<string[]>([]);
  const pastedRef = useRef<{ phone: boolean; address: boolean }>({ phone: false, address: false });

  const trackField = (field: string) => {
    if (fillStartRef.current === null) fillStartRef.current = Date.now();
    const seq = fieldSeqRef.current;
    if (seq[seq.length - 1] !== field) seq.push(field);
  };

  const resetBehavior = () => {
    fillStartRef.current = null;
    fieldSeqRef.current = [];
    pastedRef.current = { phone: false, address: false };
  };

  const collectBehavior = (): FormBehavior => ({
    phone_paste: pastedRef.current.phone,
    address_paste: pastedRef.current.address,
    form_fill_seconds: fillStartRef.current === null
      ? 0
      : Math.round(((Date.now() - fillStartRef.current) / 1000) * 10) / 10,
    field_sequence: [...fieldSeqRef.current],
  });

  const presets = {
    verified: {
      order_id: 'ORD-98241',
      phone: '+91 98711 04219',
      address: 'Flat 4B, 2nd Floor, Sunrise Apartments, Koramangala, Bangalore',
      pincode: '560034',
      order_value: 2500,
    },
    incomplete: {
      order_id: 'ORD-98240',
      phone: '+91 97533 22441',
      address: 'Plot 42, XYZ Lane',
      pincode: '560034',
      order_value: 1800,
    },
    'fraud-pattern': {
      order_id: 'ORD-98239',
      phone: '+91 99999 88888',
      address: 'Sec 12 Main Rd',
      pincode: '110001',
      order_value: 3500,
    },
  };

  const handlePreset = (key: 'verified' | 'incomplete' | 'fraud-pattern') => {
    setPayload(presets[key]);
    setPreset(key);
    setResponse(null);
    setShowDetails(false);
    setShowBreakdown(false);
    setActionResolved(false);
    setOtp('');
    setDevOtp('');
    setOtpVerified(false);
    resetBehavior();
  };

  const handleSubmit = async () => {
    setLoading(true);
    setActionResolved(false);
    setOtpVerified(false);
    setShowDetails(false);
    setShowBreakdown(false);
    try {
      const res = await axios.post<RTOOrderResponse>(
        `${BACKEND_URL}/v1/score/rto`,
        { ...payload, behavior: collectBehavior() }
      );
      setResponse(res.data);
    } catch (error) {
      console.error('Error:', error);
      alert('We could not check this order right now. Please check backend connection.');
    } finally {
      setLoading(false);
      resetBehavior();
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-semibold text-ink">Is this order safe to ship?</h2>
        <p className="text-sm text-ink-muted mt-1">
          Our AI checks the order details and flags anything that looks risky before you dispatch.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Panel - Order Form */}
        <div className="col-span-1 merchant-card p-5">
          <h3 className="text-sm font-semibold text-ink mb-4 flex items-center gap-2">
            <Search size={16} className="text-navy" />
            Check an Order
          </h3>

          {/* Presets */}
          <div className="flex flex-wrap gap-2 mb-4">
            {[
              { id: 'verified', label: 'Verified customer' },
              { id: 'incomplete', label: 'Incomplete address' },
              { id: 'fraud-pattern', label: 'Fraud pattern' },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => handlePreset(item.id as any)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                  preset === item.id
                    ? 'bg-navy text-beige font-semibold'
                    : 'bg-beige border border-border text-ink-muted hover:text-ink'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Form */}
          <div className="space-y-3 mb-5">
            <div>
              <label className="text-xs font-medium text-ink-muted mb-1 block">Your order number</label>
              <input
                type="text"
                value={payload.order_id}
                onFocus={() => trackField('order_id')}
                onChange={(e) => { trackField('order_id'); setPayload({ ...payload, order_id: e.target.value }); }}
                className="w-full bg-beige border border-border rounded px-3 py-2 text-ink text-sm focus:border-navy focus:outline-none"
                placeholder="e.g. ORD-98241"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-ink-muted mb-1 block">Customer phone number</label>
              <input
                type="text"
                value={payload.phone}
                onFocus={() => trackField('phone')}
                onPaste={() => { trackField('phone'); pastedRef.current.phone = true; }}
                onChange={(e) => { trackField('phone'); setPayload({ ...payload, phone: e.target.value }); }}
                className="w-full bg-beige border border-border rounded px-3 py-2 text-ink text-sm focus:border-navy focus:outline-none"
                placeholder="+91 Mobile number"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-ink-muted mb-1 block">Delivery address</label>
              <textarea
                value={payload.address}
                onFocus={() => trackField('address')}
                onPaste={() => { trackField('address'); pastedRef.current.address = true; }}
                onChange={(e) => { trackField('address'); setPayload({ ...payload, address: e.target.value }); }}
                className="w-full bg-beige border border-border rounded px-3 py-2 text-ink text-sm focus:border-navy focus:outline-none resize-none"
                rows={3}
                placeholder="Street address, house number"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-ink-muted mb-1 block">PIN code</label>
                <input
                  type="text"
                  value={payload.pincode}
                  onFocus={() => trackField('pincode')}
                  onChange={(e) => { trackField('pincode'); setPayload({ ...payload, pincode: e.target.value }); }}
                  className="w-full bg-beige border border-border rounded px-3 py-2 text-ink text-sm focus:border-navy focus:outline-none"
                  placeholder="6 digits"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-ink-muted mb-1 block">Order value (₹)</label>
                <input
                  type="number"
                  value={payload.order_value}
                  onFocus={() => trackField('order_value')}
                  onChange={(e) => { trackField('order_value'); setPayload({ ...payload, order_value: parseFloat(e.target.value) || 0 }); }}
                  className="w-full bg-beige border border-border rounded px-3 py-2 text-ink text-sm focus:border-navy focus:outline-none"
                  placeholder="Amount"
                />
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full btn-primary py-2.5 px-4 text-sm font-medium flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? 'Checking your order...' : 'Check this order'}
          </button>
        </div>

        {/* Right Panel - Result Card */}
        <div className="col-span-2">
          {response ? (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="merchant-card p-6 space-y-6"
            >
              {/* Zone A — Verdict */}
              {(() => {
                const verdict = getVerdictDetails(response.decision);
                const confidenceLabel = getConfidenceLabel(response.model_confidence);
                const primaryRiskSentence = humanizeRiskFactor(response.top_risk_factors[0] || '');

                return (
                  <div className="space-y-6">
                    <div className="border-b border-border pb-5">
                      <span className="text-xs font-medium text-ink-muted uppercase tracking-wider block mb-4">
                        Order Verdict
                      </span>
                      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start sm:gap-6">
                        {/* Score + arc unit */}
                        <div className="flex flex-col items-center shrink-0">
                          <span style={{ fontSize: 64, fontWeight: 700, lineHeight: 1, color: scoreColor(response.risk_score) }}>
                            {response.risk_score}
                          </span>
                          <span style={{ fontSize: 16, fontWeight: 400, color: '#000000' }}>/100</span>
                          <span style={{ fontSize: 11, fontWeight: 500, letterSpacing: '0.04em', color: scoreColor(response.risk_score) }}>
                            {scoreLabel(response.risk_score)}
                          </span>
                          <div className="mt-1">
                            <ScoreArc score={response.risk_score} color={scoreColor(response.risk_score)} />
                          </div>
                        </div>

                        {/* Verdict text */}
                        <div className="flex-1 text-center sm:text-left">
                          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded border text-base font-semibold ${verdict.badgeClass}`}>
                            {response.decision === RTODecision.APPROVE && <CheckCircle2 size={18} />}
                            {response.decision === RTODecision.REQUIRE_PREPAID && <AlertTriangle size={18} />}
                            {response.decision === RTODecision.FLAG_FOR_REVIEW && <ShieldAlert size={18} />}
                            <span>{verdict.label}</span>
                          </div>
                          <p className="mt-3 text-sm font-medium text-ink">
                            {primaryRiskSentence}
                          </p>
                          <p className="mt-1 text-sm text-ink-muted">
                            {actionResolved
                              ? 'Marked as resolved locally.'
                              : verdict.actionText}
                          </p>
                        </div>
                      </div>

                      {/* Confidence — below the score+verdict layout, right-aligned */}
                      <div className="mt-4 text-right">
                        <span style={{ fontSize: 12 }} className="text-ink-muted">Assessment accuracy: </span>
                        <span style={{ fontSize: 12 }} className="inline-block px-2.5 py-1 rounded-full font-medium bg-beige border border-border text-ink">
                          {confidenceLabel}
                        </span>
                      </div>
                    </div>

                    {/* Zone B — One-line Plain Reason */}
                    <div className="bg-beige p-4 rounded border border-border space-y-2">
                      <p className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
                        Why this decision?
                      </p>
                      <p className="text-sm font-medium text-ink">
                        {primaryRiskSentence}
                      </p>

                      {response.top_risk_factors.length > 1 && (
                        <div className="pt-2">
                          <button
                            onClick={() => setShowDetails(!showDetails)}
                            className="text-xs font-medium text-navy hover:underline flex items-center gap-1"
                          >
                            {showDetails ? 'Hide details' : 'See details'}
                            {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>

                          {showDetails && (
                            <ul className="mt-3 space-y-1.5 pl-4 list-disc text-xs text-ink-muted">
                              {response.top_risk_factors.map((factor, i) => (
                                <li key={i}>{humanizeRiskFactor(factor)}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Zone C — What to do next (action bar) */}
                    <div className="p-4 rounded bg-navy-subtle border border-navy/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold text-navy uppercase tracking-wider mb-0.5">Recommended action</p>
                        <p className="text-sm text-ink font-medium">
                          {actionResolved
                            ? 'Marked as resolved locally.'
                            : verdict.actionText}
                        </p>
                      </div>

                      {/* TODO(otp): re-enable when SMS gateway is configured.
                          Requires: Twilio / MSG91 / Fast2SMS account + RTOGUARD_SMS_KEY env var.
                          Backend endpoints already live: POST /v1/verify/send-otp + confirm-otp.

                      {response.decision === RTODecision.REQUIRE_PREPAID && !actionResolved && (
                        <div className="w-full border border-border bg-beige p-4 rounded space-y-3">
                          <p className="text-xs font-semibold text-ink uppercase tracking-wider">Confirm this order</p>
                          <p className="text-sm text-ink-muted">Ask the customer for the code before packing the order.</p>
                          {!devOtp && !otpVerified && (
                            <button onClick={async () => {
                              const result = await axios.post<{ dev_otp: string }>(`${BACKEND_URL}/v1/verify/send-otp`, { phone: payload.phone });
                              setDevOtp(result.data.dev_otp);
                            }} className="btn-primary px-3 py-1.5 text-xs">Send verification code</button>
                          )}
                          {devOtp && !otpVerified && (
                            <div className="flex flex-wrap gap-2 items-center">
                              <input aria-label="Verification code" value={otp} onChange={(event) => setOtp(event.target.value)} maxLength={4} className="w-24 bg-white border border-border rounded px-3 py-1.5 text-sm" placeholder="4 digits" />
                              <button onClick={async () => {
                                const result = await axios.post<{ verified: boolean }>(`${BACKEND_URL}/v1/verify/confirm-otp`, { phone: payload.phone, otp });
                                setOtpVerified(result.data.verified);
                              }} className="btn-primary px-3 py-1.5 text-xs">Verify</button>
                              <span className="text-xs text-ink-muted">Development code: {devOtp}</span>
                            </div>
                          )}
                          {otpVerified && <p className="text-sm font-medium text-[#1A3C6E]">Order verified by customer.</p>}
                        </div>
                      )}
                      */}

                      {response.decision === RTODecision.REQUIRE_PREPAID && !actionResolved && (
                        <button
                          onClick={() => setActionResolved(true)}
                          className="btn-primary px-3 py-1.5 text-xs whitespace-nowrap shrink-0"
                        >
                          Mark as prepaid
                        </button>
                      )}

                      {response.decision === RTODecision.FLAG_FOR_REVIEW && !actionResolved && (
                        <button
                          onClick={() => setActionResolved(true)}
                          className="px-3 py-1.5 text-xs font-medium border border-ink/30 text-ink hover:bg-beige rounded whitespace-nowrap shrink-0 transition-colors"
                        >
                          I'll review it
                        </button>
                      )}
                    </div>

                    {/* Score breakdown (collapsed by default) */}
                    <div className="border-t border-border pt-4">
                      <button
                        onClick={() => setShowBreakdown(!showBreakdown)}
                        style={{ fontSize: 13, color: '#1A3C6E' }}
                        className="font-medium hover:underline"
                      >
                        How was this score calculated?
                      </button>

                      {showBreakdown && (
                        <table className="mt-3 w-full">
                          <thead>
                            <tr>
                              <th style={{ fontSize: 11, fontWeight: 500, color: '#000000' }} className="text-left py-1.5 pr-4">
                                What we checked
                              </th>
                              <th style={{ fontSize: 11, fontWeight: 500, color: '#000000' }} className="text-left py-1.5">
                                Impact
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {response.top_risk_factors && response.top_risk_factors.length > 0 ? (
                              response.top_risk_factors.map((factor, i) => {
                                const impact = factorImpact(factor);
                                return (
                                  <tr key={i} style={{ backgroundColor: '#FFFFFF' }}>
                                    <td style={{ fontSize: 13 }} className="py-2 pr-4 text-ink">
                                      {humanizeRiskFactor(factor)}
                                    </td>
                                    <td
                                      style={{
                                        fontSize: 13,
                                        fontWeight: impact === 'Low' ? 400 : 600,
                                        color: impact === 'High' ? '#000000' : '#1A3C6E',
                                      }}
                                      className="py-2 whitespace-nowrap"
                                    >
                                      {impact}
                                    </td>
                                  </tr>
                                );
                              })
                            ) : (
                              <tr>
                                <td colSpan={2} style={{ fontSize: 13, color: '#000000' }} className="py-2">
                                  No specific flags — order looks clean.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </div>
                );
              })()}
            </motion.div>
          ) : (
            <div className="merchant-card p-8 h-full flex flex-col items-center justify-center text-center">
              <Search size={32} className="text-ink-muted mb-3 opacity-40" />
              <h4 className="text-sm font-semibold text-ink mb-1">No order checked yet</h4>
              <p className="text-xs text-ink-muted max-w-sm">
                Enter an order number, customer phone, and delivery address on the left to check if it's safe to ship.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
