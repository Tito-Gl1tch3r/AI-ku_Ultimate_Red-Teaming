package utils

import (
	"c2/config"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/dgrijalva/jwt-go"
)

type CustomClaims struct {
	Username string `json:"username"`
	jwt.StandardClaims
}

type AgentClaims struct {
	ID string `json:"id"`
	jwt.StandardClaims
}

func GenerateJWT(username string) (string, error) {
	claims := CustomClaims{
		Username: username,
		StandardClaims: jwt.StandardClaims{
			ExpiresAt: time.Now().Add(time.Hour * 24).Unix(),
			Issuer:    "C2 Server",
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(config.JWTSecret))
}

func ValidateJWT(tokenString string) (*jwt.Token, error) {
	token, err := jwt.ParseWithClaims(tokenString, &CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("invalid signing method: %v", token.Method)
		}
		return []byte(config.JWTSecret), nil
	})
	if err != nil {
		return nil, err
	}

	if claims, ok := token.Claims.(*CustomClaims); ok && token.Valid {
		if claims.ExpiresAt < time.Now().Unix() {
			return nil, fmt.Errorf("token has expired")
		}
		return token, nil
	}
	return nil, fmt.Errorf("invalid token claims")
}

func GenerateAgentToken(agentID string) (string, error) {
	claims := AgentClaims{
		ID: agentID,
		StandardClaims: jwt.StandardClaims{
			ExpiresAt: time.Now().Add(7 * 24 * time.Hour).Unix(),
			Issuer:    "C2 Server",
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(config.JWTSecret))
}

func VerifyToken(tokenString string) (string, error) {
	tokenString = strings.TrimPrefix(tokenString, "Bearer ")

	token, err := jwt.ParseWithClaims(tokenString, &AgentClaims{}, func(token *jwt.Token) (interface{}, error) {
		return []byte(config.JWTSecret), nil
	})
	if err == nil {
		if claims, ok := token.Claims.(*AgentClaims); ok && token.Valid {
			if claims.ExpiresAt < time.Now().Unix() {
				return "", fmt.Errorf("token has expired")
			}
			return claims.ID, nil
		}
	}

	token, err = jwt.ParseWithClaims(tokenString, &CustomClaims{}, func(token *jwt.Token) (interface{}, error) {
		return []byte(config.JWTSecret), nil
	})
	if err == nil {
		if claims, ok := token.Claims.(*CustomClaims); ok && token.Valid {
			if claims.ExpiresAt < time.Now().Unix() {
				return "", fmt.Errorf("token has expired")
			}
			return claims.Username, nil
		}
	}

	return "", errors.New("invalid token claims")
}
