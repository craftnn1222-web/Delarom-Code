import React, { useEffect, useState } from 'react';

const AnimatedBackground = () => {
  const [stars, setStars] = useState([]);
  const [clouds, setClouds] = useState([]);
  const [particles, setParticles] = useState([]);

  useEffect(() => {
    // Generate stars
    const starArray = [];
    for (let i = 0; i < 100; i++) {
      starArray.push({
        id: i,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        animationDelay: `${Math.random() * 3}s`,
      });
    }
    setStars(starArray);

    // Generate clouds
    const cloudArray = [];
    for (let i = 0; i < 8; i++) {
      cloudArray.push({
        id: i,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 60}%`,
        width: `${100 + Math.random() * 150}px`,
        height: `${30 + Math.random() * 40}px`,
        animationDelay: `${Math.random() * 20}s`,
      });
    }
    setClouds(cloudArray);

    // Generate particles (embers/magic)
    const particleArray = [];
    for (let i = 0; i < 20; i++) {
      particleArray.push({
        id: i,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        animationDelay: `${Math.random() * 4}s`,
      });
    }
    setParticles(particleArray);
  }, []);

  return (
    <div className="fantasy-bg">
      {/* Stars */}
      <div className="stars">
        {stars.map((star) => (
          <div
            key={star.id}
            className="star"
            style={{
              left: star.left,
              top: star.top,
              animationDelay: star.animationDelay,
            }}
          />
        ))}
      </div>

      {/* Clouds */}
      {clouds.map((cloud) => (
        <div
          key={cloud.id}
          className="cloud"
          style={{
            left: cloud.left,
            top: cloud.top,
            width: cloud.width,
            height: cloud.height,
            animationDelay: cloud.animationDelay,
          }}
        />
      ))}

      {/* Flying Dragons */}
      <div className="dragon" style={{ top: '20%' }}>🐉</div>
      <div className="dragon dragon-reverse" style={{ top: '60%' }}>🐉</div>

      {/* Lightning effect */}
      <div className="lightning" />

      {/* Floating particles */}
      <div className="particles">
        {particles.map((particle) => (
          <div
            key={particle.id}
            className="particle"
            style={{
              left: particle.left,
              top: particle.top,
              animationDelay: particle.animationDelay,
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default AnimatedBackground;