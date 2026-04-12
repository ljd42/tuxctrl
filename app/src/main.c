/*
 * Copyright (c) 2021 Bosch Sensortec GmbH
 * Copyright (c) 2026 Loic Domaigne
 *
 * SPDX-License-Identifier: Apache-2.0
 */
/* modified sample from sample zephyr/samples/sensor/bmi270 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/sensor.h> 

/* zsl - zephyr scientific library aka zscilib 
 * provide sensor fusion algorithm like Madwick, Kalmann filter, AQUA... 
 */
#include <zsl/zsl.h>
#include <zsl/orientation/orientation.h>

#include <stdio.h>

/* reading frequency to use the the BMI270
 * before to use of the allow frequency, see Datasheet
 *
 * P.S> yes I could have an enum of the valid frequency, but it's getting late
 *      and I'm now just too lazy to lookup the datasheet
 */
const unsigned int sensor_frequency = 25;
const unsigned int period_in_ms = 1000/sensor_frequency;


/* algorithm parameter for filtering */
static struct zsl_fus_aqua_cfg aqua_cfg = {
        .alpha = 0.1,
        .beta  = 0.1,
        .e_a   = 0.9,
        .e_m   = 0.9
};


/*----------------------------------------------------------------------------
 * update the position based on the current acceleration/gyro value 
 * The sensor fusion algorithm used is:
 * AQUA - Algebraic Quaternions from Roberto Valenti
 *
 * See: https://ahrs.readthedocs.io/en/latest/filters/aqua.html
 *----------------------------------------------------------------------------
 */
void 
fusion_update(struct sensor_value* acc, struct sensor_value* gyr)
{
	/* current quaternion, represent initial position of the board */
        static struct zsl_quat q = { .r = 1.0, .i = 0.0, .j = 0.0, .k = 0.0 };
        /* quaternion converted to Euleur angle (roll, pitch, yaw) */
        static struct zsl_euler e = { 0 };
	/* store the acceleration, gyroscope value as float vector with 3 components */
        static ZSL_VECTOR_DEF(av, 3);
        static ZSL_VECTOR_DEF(gv, 3);

	/* convert acceleration/gyro to float vector. Manual loop unrolling :) */
        av.data[0] = sensor_value_to_float(&acc[0]);
        av.data[1] = sensor_value_to_float(&acc[1]);
        av.data[2] = sensor_value_to_float(&acc[2]);
        gv.data[0] = sensor_value_to_float(&gyr[0]);
        gv.data[1] = sensor_value_to_float(&gyr[1]);
        gv.data[2] = sensor_value_to_float(&gyr[2]);
       
	/* update quaternion with the current av/gv data */
        zsl_fus_aqua_feed(&av, NULL, &gv, NULL, &q, &aqua_cfg);

	/* convert quaternion's position to Euler angle */
        zsl_quat_to_euler(&q, &e);
	/* use degree instead of radian (user output friendly, but inefficient for the 3d viewer engine) */
        e.x *= 180. / ZSL_PI;
        e.y *= 180. / ZSL_PI;
        e.z *= 180. / ZSL_PI;

        /* swap x and y angle to have x pointing from the cable toward the user.
	 * ( The axis used by the sensor are printed on the board ) 
	 * 
	 * send value using the following format
	 * HAMI|r:p:y|IMAH\n, where r,p,y are the Euler angles 
	 *
	 * The use of HAMI string (short for Hamilton, the inventor of Quaternions) allows to sync the byte stream
	 * stdout is redirected to the CDC/ACM "uart", this happens at Kconfig level (through prj.conf)
	 */
        printf("HAMI|%f:%f:%f|IMAH\n",e.y,e.x,e.z);
};


/*----------------------------------------------------------------------------
 * main- entry point after the C-environment has been initialized 
 *
 * the following is mostly the original sensor sample code for the BMI270 
 *----------------------------------------------------------------------------
 */
int main(void)
{
	const struct device *const dev = DEVICE_DT_GET_ONE(bosch_bmi270);
	struct sensor_value acc[3], gyr[3];
	struct sensor_value full_scale, sampling_freq, oversampling;

	if (!device_is_ready(dev)) {
		printf("Device %s is not ready\n", dev->name);
		return 0;
	}

	printf("Device %p name is %s\n", dev, dev->name);

	/* Setting scale in G, due to loss of precision if the SI unit m/s^2
	 * is used
	 */
	full_scale.val1 = 2;            /* G */
	full_scale.val2 = 0;
	sampling_freq.val1 = sensor_frequency; /* Hz. Performance mode */
	sampling_freq.val2 = 0;
	oversampling.val1 = 1;          /* Normal mode */
	oversampling.val2 = 0;

	sensor_attr_set(dev, SENSOR_CHAN_ACCEL_XYZ, SENSOR_ATTR_FULL_SCALE,
			&full_scale);
	sensor_attr_set(dev, SENSOR_CHAN_ACCEL_XYZ, SENSOR_ATTR_OVERSAMPLING,
			&oversampling);
	/* Set sampling frequency last as this also sets the appropriate
	 * power mode. If already sampling, change to 0.0Hz before changing
	 * other attributes
	 */
	sensor_attr_set(dev, SENSOR_CHAN_ACCEL_XYZ,
			SENSOR_ATTR_SAMPLING_FREQUENCY,
			&sampling_freq);


	/* Setting scale in degrees/s to match the sensor scale */
	full_scale.val1 = 500;          /* dps */
	full_scale.val2 = 0;
	sampling_freq.val1 = sensor_frequency;       /* Hz. Performance mode */
	sampling_freq.val2 = 0;
	oversampling.val1 = 1;          /* Normal mode */
	oversampling.val2 = 0;

	sensor_attr_set(dev, SENSOR_CHAN_GYRO_XYZ, SENSOR_ATTR_FULL_SCALE,
			&full_scale);
	sensor_attr_set(dev, SENSOR_CHAN_GYRO_XYZ, SENSOR_ATTR_OVERSAMPLING,
			&oversampling);
	/* Set sampling frequency last as this also sets the appropriate
	 * power mode. If already sampling, change sampling frequency to
	 * 0.0Hz before changing other attributes
	 */
	sensor_attr_set(dev, SENSOR_CHAN_GYRO_XYZ,
			SENSOR_ATTR_SAMPLING_FREQUENCY,
			&sampling_freq);

	/* warm-up the AQUA filter */
        zsl_fus_aqua_init((float)sensor_frequency, &aqua_cfg);

	while (1) {
		/* it's by no mean the most precise way, but good enough for a demo */
		k_sleep(K_MSEC(period_in_ms));

		sensor_sample_fetch(dev);
		sensor_channel_get(dev, SENSOR_CHAN_ACCEL_XYZ, acc);
		sensor_channel_get(dev, SENSOR_CHAN_GYRO_XYZ, gyr);

		/* instead of printing the accelation/gyro as in the original demo, we use 
		 * the AQUA fusion algorithm to update the position */
		fusion_update(acc,gyr);
	}

	return 0;
}
