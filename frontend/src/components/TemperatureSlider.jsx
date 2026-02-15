export default function TemperatureSlider({ temperature, onChange }) {
  return (
    <div className="temperature-slider">
      <label className="temperature-label">
        Temp: {temperature.toFixed(1)}
      </label>
      <input
        type="range"
        min="0"
        max="2"
        step="0.1"
        value={temperature}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="temperature-range"
      />
    </div>
  )
}
